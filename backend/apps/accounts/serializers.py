"""Accounts — 序列化器"""
import re
from rest_framework import serializers
from apps.accounts.models import FamilyMember, User


class FamilyMemberSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = FamilyMember
        fields = ["id", "household", "name", "role", "role_display", "student_id",
                  "face_encoding", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "household", "created_at", "updated_at"]

    def validate_face_encoding(self, value):
        if value is not None and len(value) != 128:
            raise serializers.ValidationError("人脸编码必须是 128 维向量")
        return value


# ── 注册相关 ──────────────────────────────────────────────────────

class SendSmsSerializer(serializers.Serializer):
    phone = serializers.CharField(min_length=11, max_length=16)

    def validate_phone(self, value):
        if not re.match(r'^1[3-9]\d{9}$', value):
            raise serializers.ValidationError("请输入有效的手机号")
        return value


class RegisterSerializer(serializers.Serializer):
    phone = serializers.CharField(min_length=11, max_length=16)
    password = serializers.CharField(min_length=6, max_length=128, write_only=True)
    password_confirm = serializers.CharField(write_only=True)
    sms_code = serializers.CharField(min_length=4, max_length=6)
    captcha_session_key = serializers.CharField(max_length=64)
    captcha_answer = serializers.CharField(max_length=16)

    def validate_phone(self, value):
        if not re.match(r'^1[3-9]\d{9}$', value):
            raise serializers.ValidationError("请输入有效的手机号")
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("该手机号已注册")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "两次密码不一致"})
        return attrs


class LoginSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=16)
    password = serializers.CharField(write_only=True)
