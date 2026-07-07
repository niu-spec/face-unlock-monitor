"""检测 API 蓝图 — 危险区域与异常检测接口。

提供检测相关的 REST API 端点：
  - POST /api/detection/analyze    对单帧执行检测分析
  - GET  /api/detection/status     获取检测服务运行状态

由团队成员 D（李东礼）负责实现和维护。
"""

import logging
from io import BytesIO

import cv2
import numpy as np
from flask import Blueprint, jsonify, request
from PIL import Image

from services.detection_service import DetectionService

logger = logging.getLogger(__name__)

detection_bp = Blueprint("detection", __name__, url_prefix="/api/detection")

# 全局检测服务实例（单例，维持告警冷却状态）
_detection_service = DetectionService()


@detection_bp.route("/analyze", methods=["POST"])
def analyze_frame():
    """对上传的单帧图像执行完整的危险区域与异常检测。

    Request (multipart/form-data):
        image:         图像文件（jpg/png）。
        stream_id:     摄像头流 ID（必填）。
        zones:         危险区域配置 JSON 字符串（可选）。
        person_boxes:  已检测的人体框 JSON 字符串（可选）。
        face_roles:    人脸识别角色 JSON 字符串（可选）。

    Returns:
        {
            "success": true,
            "results": [
                {
                    "alert_type": "FIRE",
                    "message": "...",
                    "bbox": [x, y, w, h],
                    "severity": "high",
                    "detail": {...}
                }
            ]
        }
    """
    if "image" not in request.files:
        return jsonify({"success": False, "error": "缺少 image 文件"}), 400

    stream_id = request.form.get("stream_id", "default")

    # 读取并解码图像
    file = request.files["image"]
    try:
        img = Image.open(BytesIO(file.read()))
        frame = cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2BGR)
    except Exception as e:
        logger.error("Failed to decode image: %s", e)
        return jsonify({"success": False, "error": f"图像解码失败: {e}"}), 400

    # 解析可选参数
    zones = _parse_json_param(request.form.get("zones"))
    person_boxes = _parse_json_param(request.form.get("person_boxes"))
    face_roles_raw = _parse_json_param(request.form.get("face_roles"))
    # face_roles 的 key 在 JSON 中为字符串，转为 int
    face_roles = {}
    if isinstance(face_roles_raw, dict):
        face_roles = {int(k): v for k, v in face_roles_raw.items()}

    # 执行检测
    results = _detection_service.process_frame(
        frame=frame,
        stream_id=stream_id,
        zones=zones,
        person_boxes=person_boxes,
        face_roles=face_roles,
    )

    return jsonify({"success": True, "results": results})


@detection_bp.route("/status", methods=["GET"])
def detection_status():
    """获取检测服务运行状态。

    Returns:
        {
            "success": true,
            "status": "running",
            "service": "DetectionService",
            "capabilities": ["ZONE_INTRUSION", "FLOOD", "FIRE", "FALL"]
        }
    """
    return jsonify(
        {
            "success": True,
            "status": "running",
            "service": "DetectionService",
            "capabilities": [
                "ZONE_INTRUSION",
                "FLOOD",
                "FIRE",
                "FALL",
            ],
        }
    )


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


def _parse_json_param(value: str | None):
    """安全解析 JSON 字符串参数。

    Args:
        value: JSON 字符串或 None。

    Returns:
        解析后的 Python 对象，或 None。
    """
    if not value:
        return None
    import json

    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return None


def get_detection_service() -> DetectionService:
    """获取全局检测服务实例。

    供其他模块（如 video.py）在视频处理流水线中直接调用
    process_frame() 方法。

    Returns:
        全局唯一的 DetectionService 实例。
    """
    return _detection_service