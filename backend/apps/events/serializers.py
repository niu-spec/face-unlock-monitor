"""Events — 序列化器"""
from rest_framework import serializers
from apps.events.models import Event


class EventSerializer(serializers.ModelSerializer):
    """事件日志序列化"""

    event_type_display = serializers.CharField(source="get_event_type_display", read_only=True)
    snapshot_url = serializers.CharField(read_only=True)
    clip_url = serializers.CharField(read_only=True)

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
            "clip_path",
            "clip_url",
            "metadata",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

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
        return data
