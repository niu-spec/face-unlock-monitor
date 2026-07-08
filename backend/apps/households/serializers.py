"""Households — 序列化器"""
from rest_framework import serializers
from .models import Household, HouseholdMembership, JoinApplication, Camera


class HouseholdSerializer(serializers.ModelSerializer):
    member_count = serializers.IntegerField(read_only=True, default=0)
    is_admin = serializers.SerializerMethodField()

    class Meta:
        model = Household
        fields = ["id", "name", "created_by", "created_at", "member_count", "is_admin"]
        read_only_fields = ["id", "created_by", "created_at"]

    def get_is_admin(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.memberships.filter(user=request.user, role="admin").exists()


class MembershipSerializer(serializers.ModelSerializer):
    user_phone = serializers.CharField(source="user.phone", read_only=True)
    user_id = serializers.IntegerField(source="user.id", read_only=True)

    class Meta:
        model = HouseholdMembership
        fields = ["id", "user_id", "user_phone", "role", "joined_at"]


class JoinApplicationSerializer(serializers.ModelSerializer):
    applicant_phone = serializers.CharField(source="applicant.phone", read_only=True)

    class Meta:
        model = JoinApplication
        fields = ["id", "household", "applicant", "applicant_phone", "status", "message", "created_at"]
        read_only_fields = ["id", "created_at", "applicant"]


class CameraSerializer(serializers.ModelSerializer):
    class Meta:
        model = Camera
        fields = ["id", "name", "household", "rtsp_url", "stream_id", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]
