from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_GET

from .services import (
    FRAME_SKIP,
    RTMP_PUBLIC_BASE_URL,
    RTSP_BASE_URL,
    STREAM_ID_PATTERN,
    build_public_rtmp_url,
    build_rtsp_url,
    ensure_worker_for_query,
    gen_frames,
    get_liveness_status,
    get_workers_status,
    resolve_presence_payload,
    resolve_presence_stream_id,
    resolve_video_stream_id,
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
def video_presence(request):
    """轻量 presence 接口，供 WebRTC Canvas 高频轮询。"""
    from apps.face.services import get_face_service

    query_stream_id = request.GET.get("stream_id")
    ensure_worker_for_query(query_stream_id)

    biz_stream_id = resolve_presence_stream_id(query_stream_id)
    service = get_face_service()
    liveness_all = get_liveness_status()
    workers = get_workers_status()
    video_id = resolve_video_stream_id(query_stream_id)
    worker = workers.get(video_id) if video_id else None
    presence, stream_live = resolve_presence_payload(service, biz_stream_id, worker)

    return JsonResponse(
        {
            "code": 200,
            "presence": presence,
            "stream_live": stream_live,
            "liveness": liveness_all.get(biz_stream_id) if biz_stream_id else None,
            "last_frame_at": worker.get("last_frame_at") if worker else None,
        }
    )


@require_GET
def video_status(request):
    from apps.face.services import get_face_service

    query_stream_id = request.GET.get("stream_id")
    ensure_worker_for_query(query_stream_id)

    service = get_face_service()
    stream_id = resolve_presence_stream_id(query_stream_id)
    workers = get_workers_status()
    video_id = resolve_video_stream_id(query_stream_id)
    worker = workers.get(video_id) if video_id else None
    presence, stream_live = resolve_presence_payload(service, stream_id, worker)

    presences = {}
    for biz_id, video_key in (("living_room", "1"), ("kitchen", "2")):
        item_worker = workers.get(video_key)
        item_presence, item_live = resolve_presence_payload(
            service, biz_id, item_worker
        )
        if item_live or item_presence.get("total", 0) > 0:
            presences[biz_id] = item_presence

    return JsonResponse(
        {
            "code": 200,
            "message": "video stream app running",
            "rtsp_base_url": RTSP_BASE_URL,
            "rtmp_public_base_url": RTMP_PUBLIC_BASE_URL,
            "presence": presence,
            "stream_live": stream_live,
            "presences": presences,
            "liveness": get_liveness_status(),
            "workers": workers,
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
