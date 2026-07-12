"""Alerts — 序列化器"""
from rest_framework import serializers
from apps.alerts.models import Alert


class AlertSerializer(serializers.ModelSerializer):
    """告警序列化"""

    type_display = serializers.CharField(source="get_type_display", read_only=True)
    level_display = serializers.CharField(source="get_level_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    snapshot_url = serializers.CharField(read_only=True)
    clip_url = serializers.CharField(read_only=True)
    assigned_to_name = serializers.CharField(read_only=True)

    class Meta:
        model = Alert
        fields = "__all__"
        read_only_fields = [
            "id", "created_at", "handled_at",
            "escalation_level", "escalation_last_at", "notified_at",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        filename = data.get("snapshot_path") or ""
        if filename:
            request = self.context.get("request")
            path = f"/api/snapshots/{filename}/"
            data["snapshot_url"] = request.build_absolute_uri(path) if request else path
        else:
            data["snapshot_url"] = None
        clip_name = data.get("clip_path") or ""
        if clip_name:
            request = self.context.get("request")
            path = f"/api/clips/{clip_name}/"
            data["clip_url"] = request.build_absolute_uri(path) if request else path
        else:
            data["clip_url"] = None
        data["assigned_to_name"] = instance.assigned_to.phone if instance.assigned_to_id else ""
        return data
