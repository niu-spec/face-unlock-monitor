"""Events — 序列化器"""
from rest_framework import serializers
from apps.common.serializers import SnapshotUrlMixin
from apps.events.models import Event


class EventSerializer(SnapshotUrlMixin, serializers.ModelSerializer):
    """事件日志序列化"""

    event_type_display = serializers.CharField(source="get_event_type_display", read_only=True)

    class Meta:
        model = Event
        fields = [
            "id",
            "event_type",
            "event_type_display",
            "stream_id",
            "description",
            "snapshot_path",
            "snapshot_url",
            "metadata",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
