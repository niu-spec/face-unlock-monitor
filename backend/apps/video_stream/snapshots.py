"""告警/事件时刻的视频帧截图持久化。"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)

_FILENAME_SAFE = re.compile(r"[^\w.-]+")


def _snapshot_root() -> Path:
    from django.conf import settings

    configured = getattr(settings, "SNAPSHOT_ROOT", None)
    root = (
        Path(configured)
        if configured
        else Path(settings.BASE_DIR / "snapshots")
    )
    root.mkdir(parents=True, exist_ok=True)
    return root


def save_event_snapshot(frame: np.ndarray, stream_id: str, tag: str) -> str:
    """将 BGR 帧保存为 JPEG，返回文件名（不含目录）。"""
    if frame is None or frame.size == 0:
        return ""

    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    safe_stream = _FILENAME_SAFE.sub("_", str(stream_id or "stream").strip()) or "stream"
    safe_tag = _FILENAME_SAFE.sub("_", str(tag or "event").strip()) or "event"
    filename = f"{ts}_{safe_stream}_{safe_tag}.jpg"
    filepath = _snapshot_root() / filename

    try:
        ok = cv2.imwrite(str(filepath), frame)
        if not ok:
            logger.warning("截图写入失败: %s", filepath)
            return ""
        return filename
    except Exception:
        logger.exception("保存事件截图失败: %s", filepath)
        return ""


def resolve_snapshot_path(filename: str) -> Path | None:
    """解析并校验截图文件路径，防止目录穿越。"""
    if not filename:
        return None
    name = Path(filename).name
    if name != filename or ".." in filename:
        return None
    filepath = _snapshot_root() / name
    return filepath if filepath.is_file() else None
