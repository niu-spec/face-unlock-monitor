from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_GET

from .services import (
    FRAME_SKIP,
    RTMP_PUBLIC_BASE_URL,
    RTSP_BASE_URL,
    STREAM_ID_PATTERN,
    build_public_rtmp_url,
    build_rtsp_url,
    gen_frames,
    get_workers_status,
)


def _invalid_stream_response():
    return JsonResponse({"code": 400, "message": "invalid stream_id"}, status=400)


@require_GET
def video_feed(request, stream_id):
    if not STREAM_ID_PATTERN.match(stream_id):
        return _invalid_stream_response()

    return StreamingHttpResponse(
        gen_frames(stream_id),
        content_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-cache"},
    )


@require_GET
def video_status(request):
    return JsonResponse(
        {
            "code": 200,
            "message": "video stream app running",
            "rtsp_base_url": RTSP_BASE_URL,
            "rtmp_public_base_url": RTMP_PUBLIC_BASE_URL,
            "workers": get_workers_status(),
        }
    )


@require_GET
def video_source(request, stream_id):
    if not STREAM_ID_PATTERN.match(stream_id):
        return _invalid_stream_response()

    return JsonResponse(
        {
            "code": 200,
            "stream_id": stream_id,
            "stream_url": build_rtsp_url(stream_id),
            "rtsp_url": build_rtsp_url(stream_id),
            "rtmp_url": build_public_rtmp_url(stream_id),
            "mjpeg_url": f"/video_feed/{stream_id}",
            "frame_skip": FRAME_SKIP,
        }
    )
