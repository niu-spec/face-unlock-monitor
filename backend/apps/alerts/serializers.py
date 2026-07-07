"""Alerts — 序列化器"""
from rest_framework import serializers
from apps.alerts.models import Alert


class AlertSerializer(serializers.ModelSerializer):
    """告警序列化"""

    type_display = serializers.CharField(source="get_type_display", read_only=True)
    level_display = serializers.CharField(source="get_level_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Alert
        fields = [
            "id",
            "household",
            "type",
            "type_display",
            "level",
            "level_display",
            "stream_id",
            "description",
            "snapshot_path",
            "status",
            "status_display",
            "created_at",
            "handled_at",
        ]
        read_only_fields = ["id", "household", "created_at", "handled_at"]
