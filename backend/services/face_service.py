"""Face recognition, family registration, and presence statistics service."""

from __future__ import annotations

import base64
import json
import os
import threading
import time
from collections import deque
from copy import deepcopy
from pathlib import Path
from typing import Any

import cv2
import face_recognition
import numpy as np


class FaceService:
    """Recognize registered family members in OpenCV BGR frames."""

    def __init__(
        self,
        registry_path: str | Path | None = None,
        tolerance: float = 0.45,
        resize_scale: float = 0.5,
        alert_cooldown: int = 30,
    ) -> None:
        self.registry_path = Path(
            registry_path or Path(__file__).resolve().parents[1] / "registered_faces.json"
        )
        self.tolerance = tolerance
        self.resize_scale = resize_scale
        self.alert_cooldown = alert_cooldown
        self._lock = threading.RLock()
        self._members: dict[str, dict[str, Any]] = {}
        self._last_unknown_alert: dict[str, float] = {}
        self._recent_alerts: deque[dict[str, Any]] = deque(maxlen=100)
        self._presence = self._empty_presence()
        self._load_registry()

    @staticmethod
    def _empty_presence() -> dict[str, Any]:
        return {
            "total": 0,
            "family": 0,
            "stranger": 0,
            "members": [],
            "faces": [],
            "stream_id": None,
            "updated_at": None,
        }

    def _load_registry(self) -> None:
        if not self.registry_path.exists():
            return
        try:
            raw = json.loads(self.registry_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"无法读取人脸特征库: {exc}") from exc

        if not isinstance(raw, dict):
            raise RuntimeError("人脸特征库格式错误：顶层必须是对象")

        for member_id, member in raw.items():
            if not isinstance(member, dict) or len(member.get("encoding", [])) != 128:
                continue
            self._members[str(member_id)] = {
                "name": str(member.get("name", member_id)),
                "role": str(member.get("role", "family")),
                "encoding": [float(value) for value in member["encoding"]],
            }

    def _save_registry(self) -> None:
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.registry_path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(self._members, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        os.replace(temporary, self.registry_path)

    @staticmethod
    def decode_base64_image(value: str) -> np.ndarray:
        """Decode a data URL or plain Base64 string into an OpenCV BGR frame."""
        if not isinstance(value, str) or not value.strip():
            raise ValueError("image 不能为空")
        payload = value.split(",", 1)[1] if value.startswith("data:") else value
        try:
            binary = base64.b64decode(payload, validate=True)
        except (ValueError, TypeError) as exc:
            raise ValueError("image 不是有效的 Base64 图片") from exc
        frame = cv2.imdecode(np.frombuffer(binary, dtype=np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("图片解码失败")
        return frame

    @staticmethod
    def decode_image_bytes(value: bytes) -> np.ndarray:
        frame = cv2.imdecode(np.frombuffer(value, dtype=np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("图片解码失败")
        return frame

    def register_member(
        self, member_id: str, name: str, role: str, frame: np.ndarray
    ) -> dict[str, str]:
        member_id = str(member_id).strip()
        name = str(name).strip()
        role = str(role).strip()
        if not member_id or not name or not role:
            raise ValueError("member_id、name 和 role 均不能为空")
        if frame is None or frame.size == 0:
            raise ValueError("图片为空")

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        locations = face_recognition.face_locations(rgb, model="hog")
        if len(locations) == 0:
            raise ValueError("图片中未检测到人脸")
        if len(locations) > 1:
            raise ValueError("注册图片必须且只能包含一张人脸")
        encodings = face_recognition.face_encodings(rgb, locations)
        if not encodings:
            raise ValueError("无法提取人脸特征")

        with self._lock:
            self._members[member_id] = {
                "name": name,
                "role": role,
                "encoding": encodings[0].astype(float).tolist(),
            }
            self._save_registry()
        return {"member_id": member_id, "name": name, "role": role}

    def _known_encodings(self) -> tuple[list[str], list[np.ndarray]]:
        with self._lock:
            member_ids = list(self._members)
            encodings = [
                np.asarray(self._members[mid]["encoding"], dtype=np.float64)
                for mid in member_ids
            ]
        return member_ids, encodings

    def process_frame(
        self, frame: np.ndarray, stream_id: str = "default", annotate: bool = True
    ) -> tuple[np.ndarray, dict[str, Any], list[dict[str, Any]]]:
        """Return annotated frame, presence state, and new FACE_UNKNOWN events."""
        if frame is None or frame.size == 0:
            raise ValueError("视频帧为空")

        scale = self.resize_scale
        analysis_frame = (
            cv2.resize(frame, None, fx=scale, fy=scale) if scale != 1.0 else frame
        )
        rgb = cv2.cvtColor(analysis_frame, cv2.COLOR_BGR2RGB)
        locations = face_recognition.face_locations(rgb, model="hog")
        encodings = face_recognition.face_encodings(rgb, locations)
        member_ids, known_encodings = self._known_encodings()

        faces: list[dict[str, Any]] = []
        members: list[dict[str, str]] = []
        seen_members: set[str] = set()
        stranger_count = 0
        output = frame.copy() if annotate else frame

        for track_id, (location, encoding) in enumerate(zip(locations, encodings)):
            member_id = None
            distance = None
            if known_encodings:
                distances = face_recognition.face_distance(known_encodings, encoding)
                best_index = int(np.argmin(distances))
                distance = float(distances[best_index])
                if distance <= self.tolerance:
                    member_id = member_ids[best_index]

            top, right, bottom, left = (
                int(round(value / scale)) for value in location
            )
            if member_id is None:
                stranger_count += 1
                name, role, known = "Stranger", "stranger", False
                color = (0, 0, 255)
            else:
                with self._lock:
                    registered = self._members[member_id]
                    name, role, known = registered["name"], registered["role"], True
                color = (0, 180, 0)
                if member_id not in seen_members:
                    members.append({"member_id": member_id, "name": name, "role": role})
                    seen_members.add(member_id)

            face = {
                "track_id": track_id,
                "member_id": member_id,
                "name": name,
                "role": role,
                "known": known,
                "distance": round(distance, 4) if distance is not None else None,
                "box": {"top": top, "right": right, "bottom": bottom, "left": left},
            }
            faces.append(face)
            if annotate:
                cv2.rectangle(output, (left, top), (right, bottom), color, 2)
                label = f"{name} ({role})" if known else "Stranger"
                cv2.putText(
                    output,
                    label,
                    (left, max(20, top - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    color,
                    2,
                    cv2.LINE_AA,
                )

        now = time.time()
        presence = {
            "total": len(faces),
            "family": len(faces) - stranger_count,
            "stranger": stranger_count,
            "members": members,
            "faces": faces,
            "stream_id": str(stream_id),
            "updated_at": now,
        }
        events: list[dict[str, Any]] = []
        last_alert = self._last_unknown_alert.get(str(stream_id), 0.0)
        if stranger_count and now - last_alert >= self.alert_cooldown:
            event = {
                "alert_type": "FACE_UNKNOWN",
                "stream_id": str(stream_id),
                "message": f"检测到 {stranger_count} 名陌生人",
                "severity": "high",
                "status": "pending",
                "detected_at": now,
            }
            events.append(event)
            with self._lock:
                self._recent_alerts.appendleft(deepcopy(event))
            self._last_unknown_alert[str(stream_id)] = now

        with self._lock:
            self._presence = deepcopy(presence)
        return output, presence, events

    def get_presence(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self._presence)

    def list_members(self) -> list[dict[str, str]]:
        with self._lock:
            return [
                {"member_id": mid, "name": item["name"], "role": item["role"]}
                for mid, item in self._members.items()
            ]

    def get_recent_alerts(self) -> list[dict[str, Any]]:
        """Return recent FACE_UNKNOWN events for alert-center integration."""
        with self._lock:
            return deepcopy(list(self._recent_alerts))


_face_service = FaceService()


def get_face_service() -> FaceService:
    """Return the process-wide service used by API and video pipelines."""
    return _face_service
