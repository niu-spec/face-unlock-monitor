"""告警/事件短视频回放 — 使用 ffmpeg 从 RTSP 截取片段。"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import threading
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_FILENAME_SAFE = re.compile(r"[^\w.-]+")


def _clip_root() -> Path:
    from django.conf import settings

    configured = getattr(settings, "CLIP_ROOT", None)
    if configured:
        root = Path(configured)
    else:
        snapshot_root = getattr(settings, "SNAPSHOT_ROOT", None)
        root = Path(snapshot_root) / "clips" if snapshot_root else Path("snapshots/clips")
    root.mkdir(parents=True, exist_ok=True)
    return root


def _clip_enabled() -> bool:
    from django.conf import settings

    return getattr(settings, "EVENT_CLIP_ENABLED", True)


def _clip_duration() -> int:
    from django.conf import settings

    return max(3, int(getattr(settings, "EVENT_CLIP_SECONDS", 10)))


def _ffmpeg_bin() -> str:
    from django.conf import settings

    return str(getattr(settings, "FFMPEG_BIN", "ffmpeg"))


def build_rtsp_url_for_clip(stream_id: str) -> str:
    from apps.video_stream.services import build_rtsp_url, resolve_video_stream_id

    video_id = resolve_video_stream_id(stream_id) or stream_id
    return build_rtsp_url(video_id)


def resolve_clip_path(filename: str) -> Path | None:
    if not filename:
        return None
    name = Path(filename).name
    if name != filename or ".." in filename:
        return None
    filepath = _clip_root() / name
    return filepath if filepath.is_file() else None


def _run_ffmpeg_record(rtsp_url: str, filepath: Path, duration: int) -> bool:
    ffmpeg = _ffmpeg_bin()
    if not shutil.which(ffmpeg):
        logger.warning("未找到 ffmpeg，跳过事件短视频录制")
        return False

    strategies = [
        [
            ffmpeg,
            "-y",
            "-rtsp_transport",
            "tcp",
            "-i",
            rtsp_url,
            "-t",
            str(duration),
            "-c",
            "copy",
            "-an",
            str(filepath),
        ],
        [
            ffmpeg,
            "-y",
            "-rtsp_transport",
            "tcp",
            "-i",
            rtsp_url,
            "-t",
            str(duration),
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-an",
            "-movflags",
            "+faststart",
            str(filepath),
        ],
    ]
    for cmd in strategies:
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=duration + 30,
                check=False,
            )
            if (
                result.returncode == 0
                and filepath.is_file()
                and filepath.stat().st_size > 1024
            ):
                return True
            if result.stderr:
                logger.debug("ffmpeg clip stderr: %s", result.stderr[-500:])
        except (subprocess.TimeoutExpired, OSError) as exc:
            logger.warning("ffmpeg 录制失败: %s", exc)
    return False


def _record_clip_worker(
    alert_id: int,
    event_id: int | None,
    stream_id: str,
    tag: str,
) -> None:
    duration = _clip_duration()
    rtsp_url = build_rtsp_url_for_clip(stream_id)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    safe_stream = _FILENAME_SAFE.sub("_", str(stream_id or "stream").strip()) or "stream"
    safe_tag = _FILENAME_SAFE.sub("_", str(tag or "event").strip()) or "event"
    filename = f"{ts}_{safe_stream}_{safe_tag}.mp4"
    filepath = _clip_root() / filename

    if not _run_ffmpeg_record(rtsp_url, filepath, duration):
        return

    try:
        from apps.alerts.models import Alert
        from apps.events.models import Event

        Alert.objects.filter(id=alert_id).update(clip_path=filename)
        if event_id:
            Event.objects.filter(id=event_id).update(clip_path=filename)
    except Exception:
        logger.exception("更新告警/事件 clip_path 失败: alert_id=%s", alert_id)


def enqueue_event_clip(
    alert_id: int,
    event_id: int | None,
    stream_id: str,
    tag: str,
) -> None:
    """后台录制告警短视频，完成后写入 clip_path。"""
    if not _clip_enabled() or not alert_id:
        return
    thread = threading.Thread(
        target=_record_clip_worker,
        args=(alert_id, event_id, stream_id, tag),
        daemon=True,
        name=f"event-clip-{alert_id}",
    )
    thread.start()
