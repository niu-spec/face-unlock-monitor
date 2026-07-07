"""Accounts — 序列化器"""
from rest_framework import serializers
from apps.accounts.models import FamilyMember


class FamilyMemberSerializer(serializers.ModelSerializer):
    """家庭成员序列化"""

    role_display = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model = FamilyMember
        fields = [
            "id",
            "name",
            "role",
            "role_display",
            "student_id",
            "face_encoding",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_face_encoding(self, value):
        """校验 128 维向量长度"""
        if value is not None and len(value) != 128:
            raise serializers.ValidationError("人脸编码必须是 128 维向量")
        return value
