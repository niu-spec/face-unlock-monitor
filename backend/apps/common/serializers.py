"""序列化器公共字段。"""

from rest_framework import serializers


class SnapshotUrlMixin:
    snapshot_url = serializers.SerializerMethodField()

    def get_snapshot_url(self, obj) -> str | None:
        filename = getattr(obj, "snapshot_path", "") or ""
        if not filename:
            return None
        request = self.context.get("request")
        path = f"/api/snapshots/{filename}/"
        return request.build_absolute_uri(path) if request else path
