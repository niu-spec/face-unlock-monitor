"""事件日志服务 — 与告警联动写入回放截图索引。"""

from __future__ import annotations

from apps.events.models import Event

ALERT_TO_EVENT_TYPE = {
    "FACE_UNKNOWN": "FACE_UNKNOWN",
    "INTRUSION": "INTRUSION",
    "PROXIMITY": "PROXIMITY",
    "LOITER": "LOITER",
    "TAILGATE": "TAILGATE",
    "FIRE": "FIRE",
    "WATER": "WATER",
    "FALL": "FALL",
}


def record_event(
    *,
    event_type: str,
    stream_id: str,
    description: str,
    snapshot_path: str = "",
    metadata: dict | None = None,
    household_id: int | None = None,
) -> Event | None:
    """写入一条事件日志，供事件回放页展示。"""
    try:
        return Event.objects.create(
            event_type=event_type,
            stream_id=stream_id,
            description=description[:256],
            snapshot_path=snapshot_path or "",
            metadata=metadata or {},
            household_id=household_id,
        )
    except Exception:
        import logging

        logging.getLogger(__name__).exception("写入事件日志失败: %s", event_type)
        return None


def record_event_for_alert(
    *,
    alert_type: str,
    stream_id: str,
    description: str,
    snapshot_path: str = "",
    household_id: int | None = None,
    metadata: dict | None = None,
) -> Event | None:
    event_type = ALERT_TO_EVENT_TYPE.get(alert_type)
    if not event_type:
        return None
    return record_event(
        event_type=event_type,
        stream_id=stream_id,
        description=description,
        snapshot_path=snapshot_path,
        metadata=metadata,
        household_id=household_id,
    )
