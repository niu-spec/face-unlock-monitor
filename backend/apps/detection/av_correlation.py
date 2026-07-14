"""音视频联动缓冲器。

维护滑动时间窗口内的音频与视频检测事件。
当时间窗口内同时存在音频异常和视频异常时，
触发联动告警（severity=critical），提升异常行为的检测可靠性。

联动规则:
    CRYING  + FALL        → EMERGENCY（哭喊+摔倒 = 需救助，severity=high 非 critical）

告警通过 apps.alerts.services.create_alert() 写入。

由团队成员 D（李东礼）负责实现和维护。
"""

import logging
import threading
import time
from collections import deque
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 联动配置
# ---------------------------------------------------------------------------

AV_CORRELATION_CONFIG = {
    # Slightly longer than INTRUSION cooldown (10s) so glass/crying can still
    # pair with the next zone alert when events are a few seconds apart.
    "WINDOW_SECONDS": 15.0,          # 滑动时间窗口（秒）
    "MAX_EVENTS_PER_STREAM": 100,    # 每个流最多缓存的事件数
    "EMERGENCY_COOLDOWN": 30,        # 联动紧急告警冷却时间（秒）
}


def _avcfg(key: str):
    """从 Django settings 读取联动配置，未设置时使用默认值。"""
    try:
        from django.conf import settings

        av_cfg = getattr(settings, "DETECTION_CONFIG", {}).get("AV_CORRELATION", {})
        return av_cfg.get(key, AV_CORRELATION_CONFIG[key])
    except Exception:
        return AV_CORRELATION_CONFIG[key]


# ---------------------------------------------------------------------------
# 事件数据结构
# ---------------------------------------------------------------------------


class AudioEvent:
    """音频检测事件"""
    __slots__ = ("timestamp", "alert_type", "confidence", "stream_id")

    def __init__(
        self,
        stream_id: str,
        alert_type: str,
        confidence: float,
        timestamp: float | None = None,
    ):
        self.stream_id = stream_id
        self.alert_type = alert_type
        self.confidence = confidence
        self.timestamp = timestamp or time.time()


class VideoEvent:
    """视频检测事件"""
    __slots__ = ("timestamp", "alert_type", "confidence", "stream_id", "description")

    def __init__(
        self,
        stream_id: str,
        alert_type: str,
        confidence: float = 1.0,
        description: str = "",
        timestamp: float | None = None,
    ):
        self.stream_id = stream_id
        self.alert_type = alert_type
        self.confidence = confidence
        self.description = description
        self.timestamp = timestamp or time.time()


# ---------------------------------------------------------------------------
# 联动规则定义
# ---------------------------------------------------------------------------
# 格式: (音频告警类型集合, 视频告警类型集合) → (联动告警类型, 严重等级, 优先级)
# 优先级越大越优先（同一窗口中多个匹配时取最大优先级）

CORRELATION_RULES: list[tuple[set[str], set[str], str, str, int]] = [
    # (audio_types, video_types, emergency_type , level  , priority)
    ({"CRYING"},          {"FALL"},  "EMERGENCY", "HIGH",     70),
    ({"CRYING"},          {"INTRUSION"}, "EMERGENCY", "HIGH",  55),
    ({"GLASS_BREAK"},     {"INTRUSION"}, "EMERGENCY", "HIGH",  50),
    ({"GLASS_BREAK"},     {"FALL"},  "EMERGENCY", "MEDIUM",   40),
]

# 重要：即使没有视频告警，音频异常也独立产生告警（不依赖视频确认）。
# 联动是"增强"而非"必要条件" — 音频服务自身已独立创建告警。
# 此模块仅在两者同时触发时额外创建一条关联告警。


# ---------------------------------------------------------------------------
# AVCorrelationBuffer
# ---------------------------------------------------------------------------


class AVCorrelationBuffer:
    """音视频联动缓冲器。

    维护每个摄像头流的滑动时间窗口，记录最近 N 秒内的检测事件。
    当新的音频或视频事件入队时，检查窗口内是否存在匹配的异类事件。

    Usage:
        buffer = AVCorrelationBuffer()
        buffer.enqueue_audio_event("living_room", "CRYING", 0.85, timestamp)
        buffer.enqueue_video_event("living_room", "FALL", 1.0, "摔倒检测")

        若约 15 秒窗口内同时存在 CRYING 和 FALL:
            → 自动创建 EMERGENCY 告警
    """

    def __init__(self):
        # stream_id → {"audio": deque[AudioEvent], "video": deque[VideoEvent]}
        self._events: dict[str, dict[str, deque]] = {}
        self._last_emergency: dict[str, float] = {}  # stream_id → 上次联动告警时间
        self._lock = threading.Lock()

        logger.info(
            "AVCorrelationBuffer 已创建 (window=%.1fs)",
            _avcfg("WINDOW_SECONDS"),
        )

    # ------------------------------------------------------------------
    # 事件入队
    # ------------------------------------------------------------------

    def enqueue_audio_event(
        self,
        stream_id: str,
        alert_type: str,
        confidence: float,
        timestamp: float | None = None,
    ):
        """音频检测事件入队，并触发联动检查。"""
        event = AudioEvent(stream_id, alert_type, confidence, timestamp)
        self._enqueue(stream_id, "audio", event)
        self._check_correlation(stream_id, event, "audio")

    def enqueue_video_event(
        self,
        stream_id: str,
        alert_type: str,
        confidence: float = 1.0,
        description: str = "",
        timestamp: float | None = None,
    ):
        """视频检测事件入队，并触发联动检查。"""
        event = VideoEvent(stream_id, alert_type, confidence, description, timestamp)
        self._enqueue(stream_id, "video", event)
        self._check_correlation(stream_id, event, "video")

    # ------------------------------------------------------------------
    # 内部实现
    # ------------------------------------------------------------------

    def _enqueue(self, stream_id: str, event_type: str, event):
        """将事件加入滑动窗口。"""
        with self._lock:
            if stream_id not in self._events:
                self._events[stream_id] = {
                    "audio": deque(),
                    "video": deque(),
                }

            queue = self._events[stream_id][event_type]
            queue.append(event)

            # 清理过期事件 + 限制最大数量
            self._prune_stream(stream_id)

    def _prune_stream(self, stream_id: str):
        """清理指定流的过期事件。"""
        window = _avcfg("WINDOW_SECONDS")
        max_events = _avcfg("MAX_EVENTS_PER_STREAM")
        now = time.time()
        cutoff = now - window

        for q in self._events.get(stream_id, {}).values():
            while q and q[0].timestamp < cutoff:
                q.popleft()
            while len(q) > max_events:
                q.popleft()

    def _check_correlation(self, stream_id: str, new_event, source: str):
        """检查新事件是否与窗口内异类事件形成联动。

        Args:
            stream_id: 视频流 ID。
            new_event: 新入队的 AudioEvent 或 VideoEvent。
            source: "audio" 或 "video"。
        """
        other = "video" if source == "audio" else "audio"
        window = _avcfg("WINDOW_SECONDS")

        with self._lock:
            streams = self._events.get(stream_id)
            if not streams:
                return

            other_queue = streams[other]
            if not other_queue:
                return

            # 只检查时间窗口内的异类事件
            cutoff = new_event.timestamp - window
            candidates = [e for e in other_queue if e.timestamp >= cutoff]
            if not candidates:
                return

        # 检查联动规则
        audio_event = new_event if source == "audio" else None
        video_event = new_event if source == "video" else None

        best_match: tuple[int, dict] | None = None

        for other_event in candidates:
            if source == "audio":
                # new: audio, other: video
                rule = self._match_rule(
                    new_event.alert_type, other_event.alert_type
                )
            else:
                # new: video, other: audio
                rule = self._match_rule(
                    other_event.alert_type, new_event.alert_type
                )

            if rule is None:
                continue

            audio_types, video_types, emergency_type, level, priority = rule

            # 记录最高优先级的匹配
            if best_match is None or priority > best_match[0]:
                best_match = (
                    priority,
                    {
                        "emergency_type": emergency_type,
                        "level": level,
                        "audio_event": audio_event or other_event,
                        "video_event": video_event or other_event,
                    },
                )

        if best_match is not None:
            self._create_emergency_alert(stream_id, best_match[1])

    def _match_rule(
        self, audio_type: str, video_type: str
    ) -> tuple | None:
        """检查一对音视频告警类型是否匹配任何联动规则。

        Returns:
            (audio_types, video_types, emergency_type, level, priority) 或 None。
        """
        for audio_types, video_types, emergency_type, level, priority in CORRELATION_RULES:
            if audio_type in audio_types and video_type in video_types:
                return (audio_types, video_types, emergency_type, level, priority)
        return None

    def _create_emergency_alert(self, stream_id: str, match: dict):
        """创建音视频联动紧急告警。"""
        now = time.time()
        cooldown = _avcfg("EMERGENCY_COOLDOWN")

        # 冷却检查
        last = self._last_emergency.get(stream_id, 0)
        if now - last < cooldown:
            logger.debug(
                "联动告警冷却中: stream=%s (距上次 %.1fs < %.1fs)",
                stream_id,
                now - last,
                cooldown,
            )
            return

        self._last_emergency[stream_id] = now

        audio: AudioEvent = match["audio_event"]
        video: VideoEvent = match["video_event"]
        emergency_type = match["emergency_type"]
        level = match["level"]

        # 构建描述
        type_labels = {
            "CRYING": "哭喊",
            "GLASS_BREAK": "玻璃破碎",
            "FALL": "人员摔倒",
            "FIRE": "火情",
            "INTRUSION": "禁区闯入",
            "PROXIMITY": "禁区接近",
        }
        audio_label = type_labels.get(audio.alert_type, audio.alert_type)
        video_label = type_labels.get(video.alert_type, video.alert_type)

        description = (
            f"⚠️ 音视频联动告警：检测到{audio_label}"
            f"（置信度 {audio.confidence:.1%}）"
            f" 同时检测到{video_label}"
            f"（时间差 {abs(audio.timestamp - video.timestamp):.1f}s）"
        )

        # 写入告警
        try:
            from apps.alerts.services import create_alert
            from apps.video_stream.services import resolve_household_id_for_stream

            create_alert(
                type=emergency_type,
                level=level,
                stream_id=stream_id,
                description=description,
                household_id=resolve_household_id_for_stream(stream_id),
                metadata={
                    "source": "av_correlation",
                    "audio_type": audio.alert_type,
                    "audio_confidence": round(audio.confidence, 4),
                    "audio_timestamp": audio.timestamp,
                    "video_type": video.alert_type,
                    "video_confidence": round(video.confidence, 4),
                    "video_timestamp": video.timestamp,
                    "time_delta_s": round(abs(audio.timestamp - video.timestamp), 2),
                },
            )

            logger.warning(
                "联动紧急告警: stream=%s audio=%s(%.2f) + video=%s(%.2f) → %s(%s)",
                stream_id,
                audio.alert_type,
                audio.confidence,
                video.alert_type,
                video.confidence,
                emergency_type,
                level,
            )
        except Exception as e:
            logger.error("创建联动紧急告警失败: %s", e, exc_info=True)

    # ------------------------------------------------------------------
    # 状态查询
    # ------------------------------------------------------------------

    def get_stream_events(self, stream_id: str) -> dict:
        """获取指定流的当前缓冲事件（调试用）。"""
        with self._lock:
            streams = self._events.get(stream_id)
            if not streams:
                return {"audio": [], "video": []}

            return {
                "audio": [
                    {
                        "type": e.alert_type,
                        "confidence": round(e.confidence, 4),
                        "timestamp": e.timestamp,
                    }
                    for e in streams["audio"]
                ],
                "video": [
                    {
                        "type": e.alert_type,
                        "confidence": round(e.confidence, 4),
                        "description": e.description,
                        "timestamp": e.timestamp,
                    }
                    for e in streams["video"]
                ],
            }

    def get_status(self) -> dict:
        """获取联动缓冲器全局状态。"""
        with self._lock:
            return {
                "active_streams": list(self._events.keys()),
                "window_seconds": _avcfg("WINDOW_SECONDS"),
                "emergency_cooldown": _avcfg("EMERGENCY_COOLDOWN"),
                "rules_count": len(CORRELATION_RULES),
            }


# ---------------------------------------------------------------------------
# 全局单例
# ---------------------------------------------------------------------------

_correlation_buffer: Optional[AVCorrelationBuffer] = None
_corr_lock = threading.Lock()


def get_av_correlation_buffer() -> AVCorrelationBuffer:
    """获取全局 AVCorrelationBuffer 单例。"""
    global _correlation_buffer
    if _correlation_buffer is None:
        with _corr_lock:
            if _correlation_buffer is None:
                _correlation_buffer = AVCorrelationBuffer()
    return _correlation_buffer
