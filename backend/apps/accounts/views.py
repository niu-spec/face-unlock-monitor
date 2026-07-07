"""Accounts — 视图：登录 + 家庭成员 CRUD"""
from django.contrib.auth import authenticate
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from drf_yasg.utils import swagger_auto_schema

from apps.accounts.models import FamilyMember, Household, UserProfile
from apps.accounts.serializers import FamilyMemberSerializer


def get_household(request):
    """从请求用户获取所属家庭。管理员(superuser)返回 None 表示可看全部。"""
    user = request.user
    if user.is_superuser:
        return None
    try:
        return user.profile.household
    except UserProfile.DoesNotExist:
        return None


class HouseholdFilterMixin:
    """Mixin：自动按家庭过滤数据，创建时自动关联家庭。

    使用方式：
        class MyViewSet(HouseholdFilterMixin, ModelViewSet):
            queryset = MyModel.objects.all()
            ...

    非 superuser 用户只能看到自己 household 的数据，
    创建新记录时自动设置 household。
    """

    def get_queryset(self):
        qs = super().get_queryset()
        household = get_household(self.request)
        if household:
            qs = qs.filter(household=household)
        return qs

    def perform_create(self, serializer):
        household = get_household(self.request)
        serializer.save(household=household)


@swagger_auto_schema(
    method="post",
    tags=["认证"],
    operation_description="JWT 登录 — 提交 username + password，返回 access_token 和 refresh_token",
)
@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    """
    JWT 登录接口。

    提交 username + password，返回 access_token 和 refresh_token。
    后续请求在 Header 中携带：`Authorization: Bearer <access_token>`
    """
    username = request.data.get("username")
    password = request.data.get("password")

    if not username or not password:
        return Response(
            {"error": "请提供 username 和 password"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = authenticate(username=username, password=password)
    if user is None:
        return Response(
            {"error": "用户名或密码错误"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    refresh = RefreshToken.for_user(user)
    return Response(
        {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {"id": user.id, "username": user.username},
        }
    )


class FamilyMemberViewSet(HouseholdFilterMixin, viewsets.ModelViewSet):
    """
    家庭成员管理 — CRUD。

    每个家庭只能看到和管理自己的家庭成员。
    """

    queryset = FamilyMember.objects.filter(is_active=True)
    serializer_class = FamilyMemberSerializer

    def get_permissions(self):
        return [IsAuthenticated()]

    @swagger_auto_schema(tags=["家庭成员"])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(tags=["家庭成员"])
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(tags=["家庭成员"])
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(tags=["家庭成员"])
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(tags=["家庭成员"])
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
