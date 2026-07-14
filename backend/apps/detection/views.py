"""检测 API 视图 — 危险区域与异常检测接口。

提供检测相关的 REST API 端点：
  - POST /api/detection/analyze/       对单帧执行检测分析
  - GET  /api/detection/status/        获取检测服务运行状态
  - GET  /api/detection/audio/status/  获取音频检测服务状态 ★ v1.3

由团队成员 D（李东礼）负责实现和维护。
"""

import logging
from io import BytesIO

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

# Lazy imports — cv2/numpy/PIL 在 Python 3.14 上无预编译包，函数内懒加载
logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def analyze_frame(request):
    """对上传的单帧图像执行完整的危险区域与异常检测。

    Request (multipart/form-data):
        image:         图像文件（jpg/png）（必填）。
        stream_id:     摄像头流 ID（可选，默认 "living_room"）。
        zones:         危险区域配置 JSON 字符串（可选）。
        person_boxes:  已检测的人体框 JSON 字符串（可选）。
        face_roles:    人脸识别角色 JSON 字符串（可选）。

    Returns:
        JSON: {"success": true, "results": [...], "alerts_created": N}
    """
    try:
        import cv2
        import numpy as np
        from PIL import Image
        from .services import get_detection_service
    except ImportError as e:
        return JsonResponse(
            {"success": False, "error": f"依赖未安装: {e}"}, status=500
        )

    if "image" not in request.FILES:
        return JsonResponse(
            {"success": False, "error": "缺少 image 文件"}, status=400
        )

    stream_id = request.POST.get("stream_id", "living_room")

    # 读取并解码图像
    file = request.FILES["image"]
    try:
        img = Image.open(BytesIO(file.read()))
        frame = cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)
    except Exception as e:
        logger.error("Failed to decode image: %s", e)
        return JsonResponse(
            {"success": False, "error": f"图像解码失败: {e}"}, status=400
        )

    # 解析可选参数
    zones = _parse_json_param(request.POST.get("zones"))
    person_boxes = _parse_json_param(request.POST.get("person_boxes"))
    face_roles_raw = _parse_json_param(request.POST.get("face_roles"))
    face_roles = {}
    if isinstance(face_roles_raw, dict):
        face_roles = {int(k): v for k, v in face_roles_raw.items()}

    # 执行检测
    service = get_detection_service()
    results = service.process_frame(
        frame=frame,
        stream_id=stream_id,
        zones=zones,
        person_boxes=person_boxes,
        face_roles=face_roles,
    )

    return JsonResponse(
        {
            "success": True,
            "results": results,
            "alerts_created": len(results),
        }
    )


@require_http_methods(["GET"])
def detection_status(request):
    """获取检测服务运行状态。

    Returns:
        JSON: {"success": true, "status": "running", "capabilities": [...]}
    """
    return JsonResponse(
        {
            "success": True,
            "status": "running",
            "service": "DetectionService",
            "capabilities": [
                "INTRUSION",
                "PROXIMITY",
                "LOITER",
                "WATER",
                "FIRE",
                "FALL",
                # ★ v1.3 音频检测能力
                "CRYING",
                "GLASS_BREAK",
                "EMERGENCY",
            ],
        }
    )


@require_http_methods(["GET"])
def audio_status(request):
    """获取音频检测服务运行状态 ★ v1.3。

    Query params:
        stream_id: 可选，指定流 ID（默认返回所有活跃流的摘要）。

    Returns:
        JSON: {
            "success": true,
            "audio_service": {...},
            "audio_captures": {...},
            "av_correlation": {...}
        }
    """
    stream_id = request.GET.get("stream_id", "")

    try:
        from .audio_service import get_audio_service
        from .audio_capture import _captures
        from .av_correlation import get_av_correlation_buffer

        audio_svc = get_audio_service()
        av_buffer = get_av_correlation_buffer()

        # 全局音频服务状态
        audio_status_data = audio_svc.get_global_status()

        # 各流采集器状态
        captures_status = {}
        for sid, cap in _captures.items():
            if not stream_id or sid == stream_id:
                captures_status[sid] = cap.to_status()

        # 音视频联动状态
        av_status = av_buffer.get_status()

        # 若指定了 stream_id，附加该流的详细信息
        stream_detail = {}
        if stream_id:
            stream_status = audio_svc.get_stream_status(stream_id)
            stream_events = av_buffer.get_stream_events(stream_id)
            stream_detail = {
                "stream_status": stream_status,
                "correlation_events": stream_events,
            }

        return JsonResponse({
            "success": True,
            "audio_service": audio_status_data,
            "audio_captures": captures_status,
            "av_correlation": av_status,
            **stream_detail,
        })
    except Exception as e:
        logger.error("获取音频状态失败: %s", e, exc_info=True)
        return JsonResponse(
            {"success": False, "error": str(e)}, status=500
        )


def _parse_json_param(value):
    """安全解析 JSON 字符串参数。"""
    import json

    if not value:
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return None
