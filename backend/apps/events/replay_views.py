"""告警/事件回放截图与短视频 API。"""

from django.http import FileResponse, Http404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from apps.video_stream.clips import resolve_clip_path
from apps.video_stream.snapshots import resolve_snapshot_path


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def snapshot_file(request, filename):
    """返回告警/事件关联的 JPEG 截图，供前端回放。"""
    filepath = resolve_snapshot_path(filename)
    if filepath is None:
        raise Http404("截图不存在")
    return FileResponse(filepath.open("rb"), content_type="image/jpeg")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def clip_file(request, filename):
    """返回告警/事件关联的 MP4 短视频。"""
    filepath = resolve_clip_path(filename)
    if filepath is None:
        raise Http404("短视频不存在")
    return FileResponse(filepath.open("rb"), content_type="video/mp4")
