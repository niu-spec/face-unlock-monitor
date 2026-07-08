"""Households — 视图：家庭管理、成员管理、加入审批"""
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema

from .models import Household, HouseholdMembership, JoinApplication, Camera
from .serializers import (
    HouseholdSerializer, MembershipSerializer,
    JoinApplicationSerializer, CameraSerializer,
)


class HouseholdViewSet(viewsets.ModelViewSet):
    """
    家庭管理。

    - 创建家庭 → 自动成为管理员
    - 管理员可转让管理员、移除成员、审批加入申请
    - 任何用户可申请加入家庭
    """
    serializer_class = HouseholdSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Household.objects.filter(memberships__user=self.request.user).distinct()

    def perform_create(self, serializer):
        household = serializer.save(created_by=self.request.user)
        HouseholdMembership.objects.create(
            household=household, user=self.request.user, role="admin"
        )

    # ── 成员列表 ────────────────────────────────────────────────

    @swagger_auto_schema(tags=["家庭管理"])
    @action(detail=True, methods=["get"])
    def members(self, request, pk=None):
        """GET /api/households/{id}/members/ — 成员列表"""
        household = self.get_object()
        memberships = household.memberships.select_related("user").all()
        return Response(MembershipSerializer(memberships, many=True).data)

    # ── 转让管理员 ──────────────────────────────────────────────

    @swagger_auto_schema(tags=["家庭管理"])
    @action(detail=True, methods=["put"])
    def transfer_admin(self, request, pk=None):
        """PUT /api/households/{id}/transfer_admin/ — 转让管理员给另一个成员"""
        household = self.get_object()

        # 验证当前用户是管理员
        my_membership = household.memberships.filter(user=request.user, role="admin").first()
        if not my_membership:
            return Response({"error": "只有管理员才能转让"}, status=status.HTTP_403_FORBIDDEN)

        user_id = request.data.get("user_id")
        if not user_id:
            return Response({"error": "请提供 user_id"}, status=status.HTTP_400_BAD_REQUEST)

        target = household.memberships.filter(user_id=user_id, role="member").first()
        if not target:
            return Response({"error": "目标用户不是该家庭成员"}, status=status.HTTP_400_BAD_REQUEST)

        my_membership.role = "member"
        my_membership.save()
        target.role = "admin"
        target.save()

        return Response({"success": True, "message": "管理员权限已转让"})

    # ── 移除成员 ────────────────────────────────────────────────

    @swagger_auto_schema(tags=["家庭管理"])
    @action(detail=True, methods=["post"])
    def kick(self, request, pk=None):
        """POST /api/households/{id}/kick/ — 移除成员"""
        household = self.get_object()

        if not household.memberships.filter(user=request.user, role="admin").exists():
            return Response({"error": "只有管理员才能移除成员"}, status=status.HTTP_403_FORBIDDEN)

        user_id = request.data.get("user_id")
        if not user_id:
            return Response({"error": "请提供 user_id"}, status=status.HTTP_400_BAD_REQUEST)

        if int(user_id) == request.user.id:
            return Response({"error": "不能移除自己"}, status=status.HTTP_400_BAD_REQUEST)

        membership = household.memberships.filter(user_id=user_id).first()
        if not membership:
            return Response({"error": "该用户不是家庭成员"}, status=status.HTTP_404_NOT_FOUND)

        membership.delete()
        return Response({"success": True, "message": "成员已移除"})

    # ── 申请加入 ────────────────────────────────────────────────

    @swagger_auto_schema(tags=["家庭管理"])
    @action(detail=False, methods=["post"])
    def join(self, request):
        """POST /api/households/join/ — 申请加入家庭"""
        household_id = request.data.get("household_id")
        message = request.data.get("message", "")

        if not household_id:
            return Response({"error": "请提供 household_id"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            household = Household.objects.get(id=household_id)
        except Household.DoesNotExist:
            return Response({"error": "家庭不存在"}, status=status.HTTP_404_NOT_FOUND)

        # 已经是成员？
        if household.memberships.filter(user=request.user).exists():
            return Response({"error": "你已经是该家庭成员"}, status=status.HTTP_400_BAD_REQUEST)

        # 已有待审核申请？
        if JoinApplication.objects.filter(
            household=household, applicant=request.user, status="pending"
        ).exists():
            return Response({"error": "你已提交过申请，请等待审核"}, status=status.HTTP_400_BAD_REQUEST)

        JoinApplication.objects.create(
            household=household,
            applicant=request.user,
            message=message,
        )
        return Response({"success": True, "message": "申请已提交"})

    # ── 申请列表 ────────────────────────────────────────────────

    @swagger_auto_schema(tags=["家庭管理"])
    @action(detail=True, methods=["get"])
    def applications(self, request, pk=None):
        """GET /api/households/{id}/applications/ — 待审核申请列表（管理员）"""
        household = self.get_object()

        if not household.memberships.filter(user=request.user, role="admin").exists():
            return Response({"error": "只有管理员才能查看"}, status=status.HTTP_403_FORBIDDEN)

        apps = household.applications.filter(status="pending").select_related("applicant")
        return Response(JoinApplicationSerializer(apps, many=True).data)

    # ── 审批申请 ────────────────────────────────────────────────

    @swagger_auto_schema(tags=["家庭管理"])
    @action(detail=True, methods=["put"])
    def review(self, request, pk=None):
        """PUT /api/households/{id}/review/ — 审批加入申请"""
        household = self.get_object()

        if not household.memberships.filter(user=request.user, role="admin").exists():
            return Response({"error": "只有管理员才能审批"}, status=status.HTTP_403_FORBIDDEN)

        app_id = request.data.get("application_id")
        action = request.data.get("action")  # "approve" or "reject"

        if action not in ("approve", "reject"):
            return Response({"error": "action 必须是 approve 或 reject"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            app = JoinApplication.objects.get(id=app_id, household=household, status="pending")
        except JoinApplication.DoesNotExist:
            return Response({"error": "申请不存在或已处理"}, status=status.HTTP_404_NOT_FOUND)

        if action == "approve":
            app.status = "approved"
            # 加入家庭
            HouseholdMembership.objects.create(
                household=household, user=app.applicant, role="member"
            )
        else:
            app.status = "rejected"

        app.reviewer = request.user
        app.reviewed_at = timezone.now()
        app.save()

        return Response({"success": True, "message": f"已{app.get_status_display()}"})

    # ── 重写 destroy（管理员可删除家庭） ─────────────────────────

    def destroy(self, request, *args, **kwargs):
        household = self.get_object()
        if not household.memberships.filter(user=request.user, role="admin").exists():
            return Response({"error": "只有管理员才能删除家庭"}, status=status.HTTP_403_FORBIDDEN)
        household.delete()
        return Response({"success": True, "message": "家庭已删除"})


class CameraViewSet(viewsets.ModelViewSet):
    """摄像头管理 — 按家庭过滤"""
    serializer_class = CameraSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Camera.objects.filter(is_active=True)
        household_id = self.request.headers.get("X-Active-Household-Id")
        if household_id:
            qs = qs.filter(household_id=int(household_id))
        return qs

    def perform_create(self, serializer):
        household_id = self.request.headers.get("X-Active-Household-Id")
        if household_id:
            serializer.save(household_id=int(household_id))
        else:
            serializer.save()

    @swagger_auto_schema(tags=["摄像头"])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(tags=["摄像头"])
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(tags=["摄像头"])
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(tags=["摄像头"])
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(tags=["摄像头"])
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
