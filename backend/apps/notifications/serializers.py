"""
通知 API 序列化器。
"""

from rest_framework import serializers

from apps.notifications.models import AlertNotification, DingTalkConfig


class DingTalkConfigSerializer(serializers.ModelSerializer):
    """钉钉通知配置序列化器

    支持未保存的临时实例（household_id=None 时用于返回默认配置）。
    """

    default_assignee_name = serializers.CharField(
        source="default_assignee.phone", read_only=True, default="",
    )
    household = serializers.SerializerMethodField(read_only=True)

    def get_household(self, obj):
        try:
            return obj.household_id
        except Exception:
            return None

    class Meta:
        model = DingTalkConfig
        fields = [
            "id", "household", "webhook_url", "secret", "is_enabled",
            "escalation_timeout_high", "escalation_timeout_medium",
            "escalation_timeout_low", "default_assignee", "default_assignee_name",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "household", "created_at", "updated_at"]
        extra_kwargs = {
            "secret": {"write_only": True},
        }


class AlertNotificationSerializer(serializers.ModelSerializer):
    """通知历史记录序列化器"""

    target_user_name = serializers.CharField(
        source="target_user.phone", read_only=True,
    )

    class Meta:
        model = AlertNotification
        fields = [
            "id", "alert", "escalation_level", "target_user", "target_user_name",
            "target_dingtalk_id", "success", "error_message", "created_at",
        ]
        read_only_fields = fields
