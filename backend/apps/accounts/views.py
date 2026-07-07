"""Accounts — 视图：登录 + 家庭成员 CRUD"""
from django.contrib.auth import authenticate
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiExample

from apps.accounts.models import FamilyMember
from apps.accounts.serializers import FamilyMemberSerializer


@extend_schema(
    tags=["认证"],
    request={
        "application/json": {
            "example": {"username": "admin", "password": "123456"}
        }
    },
    responses={
        200: {
            "example": {
                "access": "eyJ...",
                "refresh": "eyJ...",
                "user": {"id": 1, "username": "admin"},
            }
        }
    },
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


class FamilyMemberViewSet(viewsets.ModelViewSet):
    """
    家庭成员管理 — CRUD。

    管理员可通过此接口管理被摄像头识别的人员：
    - 注册新成员（姓名、角色、学号）
    - 查看成员列表
    - 修改/删除成员
    """

    queryset = FamilyMember.objects.filter(is_active=True)
    serializer_class = FamilyMemberSerializer

    def get_permissions(self):
        """登录接口不需要认证，其他需要"""
        return [IsAuthenticated()]

    @extend_schema(tags=["家庭成员"])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(tags=["家庭成员"])
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(tags=["家庭成员"])
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(tags=["家庭成员"])
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(tags=["家庭成员"])
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
