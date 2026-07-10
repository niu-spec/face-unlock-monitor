"""Passive liveness and anti-spoof checks for face frames."""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict, deque
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger(__name__)

FACE_SPOOF = "FACE_SPOOF"
FACE_REPLAY = "FACE_REPLAY"
FACE_DEEPFAKE = "FACE_DEEPFAKE"


class LivenessDetectionService:
    """Stateful, dependency-light liveness detector keyed by stream_id."""

    def __init__(self, window_size: int = 8, min_samples: int = 4, alert_cooldown: int = 30) -> None:
        self.window_size = int(window_size)
        self.min_samples = int(min_samples)
        self.alert_cooldown = int(alert_cooldown)
        self._history = defaultdict(lambda: deque(maxlen=self.window_size))
        self._last_alert: dict[tuple[str, str], float] = {}
        self._lock = threading.RLock()

    def observe(
        self,
        frame: np.ndarray,
        presence: dict[str, Any],
        stream_id: str = "living_room",
        household_id: int | None = None,
        persist_alert: bool = True,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        observation = self._make_observation(frame, presence, str(stream_id))
        with self._lock:
            history = self._history[str(stream_id)]
            history.append(observation)
            result = self._evaluate(list(history))

        events: list[dict[str, Any]] = []
        attack_type = result.get("attack_type")
        if attack_type and not result.get("passed") and self._should_alert(str(stream_id), attack_type):
            event = self._build_event(result, str(stream_id))
            events.append(event)
            if persist_alert:
                self._persist_alert(event, household_id)
        return result, events

    def analyze_sequence(
        self,
        frames: list[np.ndarray],
        presences: list[dict[str, Any]],
        stream_id: str = "auth",
    ) -> dict[str, Any]:
        observations = [
            self._make_observation(frame, presence, str(stream_id))
            for frame, presence in zip(frames, presences)
        ]
        return self._evaluate(observations)

    def reset(self, stream_id: str | None = None) -> None:
        with self._lock:
            if stream_id is None:
                self._history.clear()
                self._last_alert.clear()
            else:
                self._history.pop(str(stream_id), None)

    def _make_observation(self, frame: np.ndarray, presence: dict[str, Any], stream_id: str) -> dict[str, Any]:
        face = self._primary_face(presence)
        empty = {
            "stream_id": stream_id,
            "has_face": False,
            "box": None,
            "hash": None,
            "sharpness": 0.0,
            "texture_std": 0.0,
            "edge_ratio": 0.0,
        }
        if frame is None or frame.size == 0 or face is None:
            return empty
        crop, box = self._crop_face(frame, face)
        if crop is None:
            return empty

        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        small = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA)
        edges = cv2.Canny(gray, 80, 160)
        return {
            "stream_id": stream_id,
            "has_face": True,
            "box": box,
            "hash": small >= float(small.mean()),
            "sharpness": float(cv2.Laplacian(gray, cv2.CV_64F).var()),
            "texture_std": float(gray.std()),
            "edge_ratio": float(np.count_nonzero(edges) / edges.size) if edges.size else 0.0,
        }

    @staticmethod
    def _primary_face(presence: dict[str, Any]) -> dict[str, Any] | None:
        faces = presence.get("faces") or []
        if not faces:
            return None

        def area(face: dict[str, Any]) -> int:
            box = face.get("box") or {}
            return max(0, int(box.get("right", 0)) - int(box.get("left", 0))) * max(
                0, int(box.get("bottom", 0)) - int(box.get("top", 0))
            )

        return max(faces, key=area)

    @staticmethod
    def _crop_face(frame: np.ndarray, face: dict[str, Any]) -> tuple[np.ndarray | None, tuple[int, int, int, int] | None]:
        box = face.get("box") or {}
        height, width = frame.shape[:2]
        left = max(0, min(int(box.get("left", 0)), width - 1))
        top = max(0, min(int(box.get("top", 0)), height - 1))
        right = max(left + 1, min(int(box.get("right", 0)), width))
        bottom = max(top + 1, min(int(box.get("bottom", 0)), height))
        crop = frame[top:bottom, left:right]
        if crop.size == 0:
            return None, None
        return crop, (left, top, right, bottom)

    def _evaluate(self, observations: list[dict[str, Any]]) -> dict[str, Any]:
        face_items = [item for item in observations if item.get("has_face")]
        if len(face_items) < self.min_samples:
            return {
                "passed": False,
                "status": "insufficient",
                "attack_type": None,
                "score": 0.0,
                "reason": "需要连续多帧人脸才能进行活体检测",
                "details": {"samples": len(face_items), "required": self.min_samples},
            }

        motion = self._motion_score(face_items)
        box_motion = self._box_motion_score(face_items)
        replay = self._replay_score(face_items)
        texture = self._texture_anomaly_score(face_items)
        details = self._details(face_items, motion, box_motion, replay, texture)

        if motion < 0.003 and box_motion < 0.004:
            return self._attack(FACE_SPOOF, 1.0 - max(motion, box_motion), "连续人脸区域几乎完全静止，疑似静态照片欺骗", details)
        if replay >= 0.95:
            return self._attack(FACE_REPLAY, replay, "检测到重复帧/循环播放特征，疑似视频重放攻击", details)
        if texture >= 0.9:
            return self._attack(FACE_DEEPFAKE, texture, "人脸区域纹理或清晰度异常，疑似 AI 换脸/屏幕翻拍", details)
        return {
            "passed": True,
            "status": "passed",
            "attack_type": None,
            "score": round(max(motion, 1.0 - texture), 4),
            "reason": "连续帧存在自然变化，未发现明显欺骗特征",
            "details": details,
        }

    @staticmethod
    def _attack(attack_type: str, score: float, reason: str, details: dict[str, Any]) -> dict[str, Any]:
        return {
            "passed": False,
            "status": "attack",
            "attack_type": attack_type,
            "score": round(float(score), 4),
            "reason": reason,
            "details": details,
        }

    @staticmethod
    def _motion_score(items: list[dict[str, Any]]) -> float:
        distances = []
        for prev, cur in zip(items, items[1:]):
            if prev.get("hash") is None or cur.get("hash") is None:
                continue
            distances.append(float(np.mean(prev["hash"] != cur["hash"])))
        return float(np.mean(distances)) if distances else 0.0

    @staticmethod
    def _box_motion_score(items: list[dict[str, Any]]) -> float:
        moves = []
        for prev, cur in zip(items, items[1:]):
            if prev.get("box") is None or cur.get("box") is None:
                continue
            px1, py1, px2, py2 = prev["box"]
            cx1, cy1, cx2, cy2 = cur["box"]
            pw, ph = max(1, px2 - px1), max(1, py2 - py1)
            pcx, pcy = px1 + pw / 2.0, py1 + ph / 2.0
            cw, ch = max(1, cx2 - cx1), max(1, cy2 - cy1)
            ccx, ccy = cx1 + cw / 2.0, cy1 + ch / 2.0
            moves.append(abs(ccx - pcx) / pw + abs(ccy - pcy) / ph + abs(cw - pw) / pw + abs(ch - ph) / ph)
        return float(np.mean(moves)) if moves else 0.0

    @staticmethod
    def _replay_score(items: list[dict[str, Any]]) -> float:
        hashes = [item.get("hash") for item in items if item.get("hash") is not None]
        if len(hashes) < 6:
            return 0.0
        checks = 0
        hits = 0
        for index in range(2, len(hashes)):
            checks += 1
            if float(np.mean(hashes[index] != hashes[index - 2])) < 0.01:
                hits += 1
        return hits / checks if checks else 0.0

    @staticmethod
    def _texture_anomaly_score(items: list[dict[str, Any]]) -> float:
        sharpness = np.array([item.get("sharpness", 0.0) for item in items], dtype=float)
        texture_std = np.array([item.get("texture_std", 0.0) for item in items], dtype=float)
        edge_ratio = np.array([item.get("edge_ratio", 0.0) for item in items], dtype=float)
        return max(
            float(np.mean(sharpness < 8.0)),
            float(np.mean(texture_std < 4.0)),
            float(np.mean((edge_ratio < 0.005) | (edge_ratio > 0.45))),
        )

    @staticmethod
    def _details(items: list[dict[str, Any]], motion: float, box_motion: float, replay: float, texture: float) -> dict[str, Any]:
        return {
            "samples": len(items),
            "motion_score": round(motion, 6),
            "box_motion": round(box_motion, 6),
            "replay_score": round(replay, 6),
            "texture_score": round(texture, 6),
            "avg_sharpness": round(float(np.mean([item.get("sharpness", 0.0) for item in items])), 4),
            "avg_texture_std": round(float(np.mean([item.get("texture_std", 0.0) for item in items])), 4),
            "avg_edge_ratio": round(float(np.mean([item.get("edge_ratio", 0.0) for item in items])), 6),
        }

    @staticmethod
    def _build_event(result: dict[str, Any], stream_id: str) -> dict[str, Any]:
        return {
            "type": result["attack_type"],
            "level": "HIGH",
            "stream_id": stream_id,
            "description": f"{result['reason']}，score={result['score']}",
            "details": result.get("details", {}),
        }

    def _should_alert(self, stream_id: str, attack_type: str) -> bool:
        now = time.time()
        key = (stream_id, attack_type)
        last = self._last_alert.get(key, 0.0)
        if now - last < self.alert_cooldown:
            return False
        self._last_alert[key] = now
        return True

    @staticmethod
    def _persist_alert(event: dict[str, Any], household_id: int | None) -> None:
        try:
            from apps.alerts.services import create_alert

            create_alert(
                type=event["type"],
                level=event["level"],
                stream_id=event["stream_id"],
                description=event["description"],
                household_id=household_id,
            )
        except Exception:
            logger.exception("持久化人脸活体攻击告警失败")


_liveness_service: LivenessDetectionService | None = None
_liveness_lock = threading.Lock()


def get_liveness_service() -> LivenessDetectionService:
    global _liveness_service
    if _liveness_service is None:
        with _liveness_lock:
            if _liveness_service is None:
                _liveness_service = LivenessDetectionService()
    return _liveness_service
