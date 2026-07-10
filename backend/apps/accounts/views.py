"""Accounts — 视图：注册、登录、家庭成员 CRUD"""
import random
import uuid
from datetime import timedelta

from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from drf_yasg.utils import swagger_auto_schema

from apps.households.filters import HouseholdFilterBackend, resolve_active_household_id
from apps.accounts.models import User, FamilyMember, SmsVerificationCode, Captcha
from apps.accounts.serializers import (
    FamilyMemberSerializer,
    SendSmsSerializer,
    RegisterSerializer,
    LoginSerializer,
)


# ── SMS 验证码 ─────────────────────────────────────────────────────

@swagger_auto_schema(
    method="post",
    tags=["认证"],
    operation_description="发送短信验证码（开发环境打印到控制台）",
    request_body=SendSmsSerializer,
)
@api_view(["POST"])
@permission_classes([AllowAny])
def send_sms_view(request):
    ser = SendSmsSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    phone = ser.validated_data["phone"]

    # 60s 限频
    recent = SmsVerificationCode.objects.filter(
        phone=phone, created_at__gte=timezone.now() - timedelta(seconds=60)
    ).first()
    if recent:
        return Response({"error": "发送过于频繁，请60秒后再试"}, status=status.HTTP_429_TOO_MANY_REQUESTS)

    code = f"{random.randint(100000, 999999)}"
    SmsVerificationCode.objects.create(
        phone=phone,
        code=code,
        expires_at=timezone.now() + timedelta(minutes=5),
    )

    # 开发环境：打印到控制台
    print(f"\n{'='*50}")
    print(f"[DEV SMS] 手机号: {phone}  验证码: {code}")
    print(f"{'='*50}\n")

    from django.conf import settings
    return Response({
        "success": True,
        "message": "验证码已发送",
        **({"dev_code": code} if settings.DEBUG else {}),
    })


# ── 数学 CAPTCHA ───────────────────────────────────────────────────

@swagger_auto_schema(method="get", tags=["认证"], operation_description="获取数学验证码")
@api_view(["GET"])
@permission_classes([AllowAny])
def captcha_view(request):
    a, b = random.randint(0, 99), random.randint(0, 99)
    session_key = str(uuid.uuid4())
    Captcha.objects.create(
        question=f"{a} + {b} = ?",
        answer=str(a + b),
        session_key=session_key,
    )
    return Response({"session_key": session_key, "question": f"{a} + {b} = ?"})


# ── 注册 ───────────────────────────────────────────────────────────

@swagger_auto_schema(
    method="post",
    tags=["认证"],
    operation_description="用户注册 — 验证短信码 + CAPTCHA",
    request_body=RegisterSerializer,
)
@api_view(["POST"])
@permission_classes([AllowAny])
def register_view(request):
    ser = RegisterSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    data = ser.validated_data
    phone = data["phone"]
    password = data["password"]
    sms_code = data["sms_code"]
    session_key = data["captcha_session_key"]
    captcha_answer = data["captcha_answer"]

    # 校验短信验证码
    sms = SmsVerificationCode.objects.filter(
        phone=phone, code=sms_code, is_used=False
    ).order_by("-created_at").first()

    if not sms or not sms.is_valid():
        return Response({"error": "短信验证码无效或已过期"}, status=status.HTTP_400_BAD_REQUEST)

    sms.is_used = True
    sms.save()

    # 校验 CAPTCHA
    cap = Captcha.objects.filter(
        session_key=session_key, is_used=False
    ).order_by("-created_at").first()

    if not cap or cap.answer.strip() != captcha_answer.strip():
        return Response({"error": "数学验证码错误"}, status=status.HTTP_400_BAD_REQUEST)

    cap.is_used = True
    cap.save()

    # 创建用户
    User.objects.create_user(phone=phone, password=password)

    return Response({"success": True, "message": "注册成功"}, status=status.HTTP_201_CREATED)


# ── 登录 ───────────────────────────────────────────────────────────

@swagger_auto_schema(
    method="post",
    tags=["认证"],
    operation_description="JWT 登录 — 手机号 + 密码",
    request_body=LoginSerializer,
)
@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    ser = LoginSerializer(data=request.data)
    if not ser.is_valid():
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

    phone = ser.validated_data["phone"]
    password = ser.validated_data["password"]

    user = authenticate(request, phone=phone, password=password)
    if user is None:
        return Response({"error": "手机号或密码错误"}, status=status.HTTP_401_UNAUTHORIZED)

    refresh = RefreshToken.for_user(user)
    return Response({
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": {"id": user.id, "phone": str(user.phone)},
    })


# ── 退出登录（Token 黑名单） ─────────────────────────────────────

@swagger_auto_schema(
    method="post",
    tags=["认证"],
    operation_description="退出登录 — 将 refresh token 加入黑名单，使其无法再用于刷新",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """退出登录：黑名单 refresh token，前端需同时清除本地 token"""
    refresh_token = request.data.get("refresh")
    if refresh_token:
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            pass  # token 已失效或格式错误也是 ok 的
    return Response({"success": True, "message": "已退出登录"})


# ── 当前用户信息 ───────────────────────────────────────────────────

@swagger_auto_schema(method="get", tags=["认证"], operation_description="获取当前用户信息")
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me_view(request):
    user = request.user
    households = list(
        user.memberships.select_related("household").values(
            "household__id", "household__name", "role"
        )
    )
    return Response({
        "id": user.id,
        "phone": str(user.phone),
        "dingtalk_user_id": user.dingtalk_user_id,
        "dingtalk_mobile": user.dingtalk_mobile,
        "supervisor_id": user.supervisor_id,
        "households": [
            {"id": h["household__id"], "name": h["household__name"], "role": h["role"]}
            for h in households
        ],
    })


@swagger_auto_schema(method="get", tags=["个人信息"], operation_description="获取个人信息")
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def profile_view(request):
    user = request.user
    return Response({
        "id": user.id,
        "phone": str(user.phone),
        "dingtalk_user_id": user.dingtalk_user_id,
        "dingtalk_mobile": user.dingtalk_mobile,
        "supervisor_id": user.supervisor_id,
    })


@swagger_auto_schema(method="put", tags=["个人信息"], operation_description="更新个人信息（钉钉ID、手机号等）")
@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_profile_view(request):
    """更新钉钉相关字段"""
    user = request.user

    dingtalk_user_id = request.data.get("dingtalk_user_id", None)
    dingtalk_mobile = request.data.get("dingtalk_mobile", None)
    supervisor_id = request.data.get("supervisor_id", None)

    update_fields = []
    if dingtalk_user_id is not None:
        user.dingtalk_user_id = dingtalk_user_id
        update_fields.append("dingtalk_user_id")
    if dingtalk_mobile is not None:
        user.dingtalk_mobile = dingtalk_mobile
        update_fields.append("dingtalk_mobile")
    if supervisor_id is not None:
        if supervisor_id:
            from apps.accounts.models import User
            try:
                User.objects.get(id=supervisor_id)
            except User.DoesNotExist:
                return Response({"error": "指定的上级用户不存在"}, status=400)
        user.supervisor_id = supervisor_id or None
        update_fields.append("supervisor_id")

    if update_fields:
        user.save(update_fields=update_fields)

    return Response({
        "id": user.id,
        "phone": str(user.phone),
        "dingtalk_user_id": user.dingtalk_user_id,
        "dingtalk_mobile": user.dingtalk_mobile,
        "supervisor_id": user.supervisor_id,
    })


@swagger_auto_schema(
    method="post", tags=["个人信息"],
    operation_description="更换手机号 — 需短信验证新手机号",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_phone_view(request):
    new_phone = request.data.get("phone", "")
    sms_code = request.data.get("sms_code", "")

    if not new_phone or not sms_code:
        return Response({"error": "请提供手机号和验证码"}, status=status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(phone=new_phone).exists():
        return Response({"error": "该手机号已被使用"}, status=status.HTTP_400_BAD_REQUEST)

    # 校验短信验证码
    sms = SmsVerificationCode.objects.filter(
        phone=new_phone, code=sms_code, is_used=False
    ).order_by("-created_at").first()

    if not sms or not sms.is_valid():
        return Response({"error": "短信验证码无效或已过期"}, status=status.HTTP_400_BAD_REQUEST)

    sms.is_used = True
    sms.save()

    user = request.user
    user.phone = new_phone
    user.save(update_fields=["phone"])

    return Response({"success": True, "phone": str(user.phone)})


# ── 家庭成员 CRUD ──────────────────────────────────────────────────

class FamilyMemberViewSet(viewsets.ModelViewSet):
    """家庭成员管理 — 按家庭过滤"""

    queryset = FamilyMember.objects.filter(is_active=True)
    serializer_class = FamilyMemberSerializer
    filter_backends = [HouseholdFilterBackend]

    def get_permissions(self):
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        household_id = resolve_active_household_id(self.request)
        if not household_id:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"error": "请先选择当前家庭"})
        serializer.save(household_id=household_id)

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
