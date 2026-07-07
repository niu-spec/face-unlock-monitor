"""
告警服务层 — 供 C（人脸识别）和 D（异常检测）通过 HTTP 调用。

使用方式（AI 模块通过 HTTP 调用）：
    POST http://localhost:5000/api/alerts/
    Body: {
        "type": "FACE_UNKNOWN",
        "level": "HIGH",
        "stream_id": "living_room",
        "description": "客厅检测到陌生人",
        "snapshot_path": "/snapshots/20260706_153000.jpg"
    }

也可以作为 Python 函数直接 import 使用（如果同进程）：
    from apps.alerts.services import create_alert
    create_alert(type="FACE_UNKNOWN", level="HIGH", stream_id="living_room", ...)
"""

from apps.alerts.models import Alert


def create_alert(
    type: str,
    level: str = "MEDIUM",
    stream_id: str = "living_room",
    description: str = "",
    snapshot_path: str = "",
) -> Alert:
    """
    创建告警 — 供 C/D 服务调用。

    Args:
        type: 告警类型 (FACE_UNKNOWN/INTRUSION/PROXIMITY/LOITER/TAILGATE/FIRE/WATER/FALL)
        level: 严重等级 (HIGH/MEDIUM/LOW)
        stream_id: 视频流ID (living_room/kitchen)
        description: 告警描述
        snapshot_path: 截图文件路径

    Returns:
        创建的 Alert 实例
    """
    alert = Alert.objects.create(
        type=type,
        level=level,
        stream_id=stream_id,
        description=description,
        snapshot_path=snapshot_path,
    )
    return alert


def get_pending_alerts(stream_id: str = None):
    """获取待处理的告警列表"""
    qs = Alert.objects.filter(status="pending")
    if stream_id:
        qs = qs.filter(stream_id=stream_id)
    return qs.order_by("-created_at")


def handle_alert(alert_id: int) -> Alert:
    """将告警标记为已处理"""
    from django.utils import timezone

    alert = Alert.objects.get(id=alert_id)
    alert.status = "handled"
    alert.handled_at = timezone.now()
    alert.save(update_fields=["status", "handled_at"])
    return alert
