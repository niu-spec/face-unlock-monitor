"""Zones — 序列化器"""
from rest_framework import serializers
from apps.zones.models import Zone


class ZoneSerializer(serializers.ModelSerializer):
    """安防区域序列化"""

    stream_id_display = serializers.CharField(source="get_stream_id_display", read_only=True)

    class Meta:
        model = Zone
        fields = [
            "id",
            "household",
            "name",
            "stream_id",
            "stream_id_display",
            "points_json",
            "forbidden_roles",
            "safe_distance",
            "dwell_time",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "household", "created_at", "updated_at"]
