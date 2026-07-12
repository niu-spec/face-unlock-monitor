"""
告警服务层 — 供 C（人脸识别）和 D（异常检测）通过 HTTP 调用。

使用方式（AI 模块通过 HTTP 调用）：
    POST http://localhost:8000/api/alerts/
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
    household_id: int = None,
    frame=None,
    metadata: dict | None = None,
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
    if not snapshot_path and frame is not None:
        try:
            from apps.video_stream.snapshots import save_event_snapshot

            snapshot_path = save_event_snapshot(frame, stream_id, type)
        except Exception:
            import logging

            logging.getLogger(__name__).exception(
                "保存告警截图失败，继续创建告警: %s", type
            )

    alert = Alert.objects.create(
        type=type,
        level=level,
        stream_id=stream_id,
        description=description,
        snapshot_path=snapshot_path,
        household_id=household_id,
        metadata=dict(metadata or {}),
    )

    event = None
    try:
        from apps.events.services import record_event_for_alert

        event = record_event_for_alert(
            alert_type=type,
            stream_id=stream_id,
            description=description,
            snapshot_path=snapshot_path,
            household_id=household_id,
            metadata=metadata,
        )
    except Exception:
        import logging

        logging.getLogger(__name__).exception("同步事件日志失败: %s", type)

    try:
        from apps.video_stream.clips import enqueue_event_clip

        enqueue_event_clip(
            alert.id,
            event.id if event else None,
            stream_id,
            type,
        )
    except Exception:
        import logging

        logging.getLogger(__name__).exception("启动告警短视频录制失败: %s", type)

    return alert


def get_pending_alerts(stream_id: str = None):
    """获取待处理的告警列表"""
    qs = Alert.objects.filter(status="pending")
    if stream_id:
        qs = qs.filter(stream_id=stream_id)
    return qs.order_by("-created_at")


def _finalize_alert(alert: Alert, status: str, actor=None, actor_key: str = "handled_by") -> Alert:
    """将告警标记为 handled 或 ignored，并记录操作人。"""
    from django.utils import timezone

    now = timezone.now()
    alert.status = status
    alert.handled_at = now

    if actor:
        metadata = dict(alert.metadata or {})
        metadata[actor_key] = {
            "user_id": actor.id,
            "phone": actor.phone,
        }
        metadata[f"{status}_at"] = now.isoformat()
        alert.metadata = metadata

    alert.save(update_fields=["status", "handled_at", "metadata"])
    return alert


def handle_alert(alert_id: int, handled_by=None) -> Alert:
    """将告警标记为已处理"""
    alert = Alert.objects.get(id=alert_id)
    return _finalize_alert(alert, "handled", handled_by, "handled_by")


def ignore_alert(alert_id: int, ignored_by=None) -> Alert:
    """将告警标记为已忽略"""
    alert = Alert.objects.get(id=alert_id)
    return _finalize_alert(alert, "ignored", ignored_by, "ignored_by")
