"""Face detection, 128-d encoding, matching, and presence statistics."""

from __future__ import annotations

import base64
import json
import os
import threading
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np


def _load_face_recognition():
    """Load the native dependency lazily so Django management commands still start."""
    try:
        import face_recognition
    except ImportError as exc:
        raise RuntimeError(
            "face_recognition 未安装，请按 backend/dat/README.md 配置 dlib 环境"
        ) from exc
    return face_recognition


def _default_registry_path() -> Path:
    try:
        from django.conf import settings

        if settings.configured:
            return Path(
                getattr(
                    settings,
                    "FACE_REGISTRY_PATH",
                    settings.BASE_DIR / "registered_faces.json",
                )
            )
    except Exception:
        pass
    return Path(__file__).resolve().parents[2] / "registered_faces.json"


class FaceRecognitionService:
    """Process OpenCV BGR frames and maintain the latest presence snapshot."""

    def __init__(
        self,
        registry_path: str | Path | None = None,
        tolerance: float = 0.45,
        resize_scale: float = 0.5,
        unknown_alert_cooldown: int = 30,
    ) -> None:
        self.registry_path = Path(registry_path or _default_registry_path())
        self.tolerance = float(tolerance)
        self.resize_scale = float(resize_scale)
        self.unknown_alert_cooldown = int(unknown_alert_cooldown)
        self._lock = threading.RLock()
        self._members: dict[str, dict[str, Any]] = {}
        self._last_unknown_alert: dict[str, float] = {}
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
            raise RuntimeError("registered_faces.json 顶层必须是对象")
        for member_id, member in raw.items():
            if not isinstance(member, dict) or len(member.get("encoding", [])) != 128:
                continue
            self._members[str(member_id)] = {
                "name": str(member.get("name", member_id)),
                "role": str(member.get("role", "adult")),
                "household_id": member.get("household_id"),
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
    def decode_image_bytes(value: bytes) -> np.ndarray:
        frame = cv2.imdecode(np.frombuffer(value, dtype=np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("图片解码失败，仅支持常见 JPG/PNG 图片")
        return frame

    @classmethod
    def decode_base64_image(cls, value: str) -> np.ndarray:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("image 不能为空")
        payload = value.split(",", 1)[1] if value.startswith("data:") else value
        try:
            binary = base64.b64decode(payload, validate=True)
        except (ValueError, TypeError) as exc:
            raise ValueError("image 不是有效的 Base64 图片") from exc
        return cls.decode_image_bytes(binary)

    def encode_single_face(self, frame: np.ndarray) -> np.ndarray:
        if frame is None or frame.size == 0:
            raise ValueError("图片为空")
        face_recognition = _load_face_recognition()
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        locations = face_recognition.face_locations(rgb, model="hog")
        if not locations:
            raise ValueError("图片中未检测到人脸")
        if len(locations) != 1:
            raise ValueError("注册图片必须且只能包含一张人脸")
        encodings = face_recognition.face_encodings(rgb, locations)
        if not encodings or len(encodings[0]) != 128:
            raise ValueError("无法提取128维人脸特征")
        return np.asarray(encodings[0], dtype=np.float64)

    def register_encoding(
        self,
        member_id: str | int,
        name: str,
        role: str,
        encoding: np.ndarray | list[float],
        household_id: int | None = None,
    ) -> dict[str, Any]:
        member_id = str(member_id).strip()
        values = np.asarray(encoding, dtype=np.float64)
        if not member_id or not str(name).strip() or not str(role).strip():
            raise ValueError("member_id、name 和 role 均不能为空")
        if values.shape != (128,):
            raise ValueError("人脸编码必须是128维")
        with self._lock:
            self._members[member_id] = {
                "name": str(name).strip(),
                "role": str(role).strip(),
                "household_id": household_id,
                "encoding": values.astype(float).tolist(),
            }
            self._save_registry()
        return {
            "member_id": member_id,
            "name": str(name).strip(),
            "role": str(role).strip(),
            "household_id": household_id,
        }

    def register_member(
        self,
        member_id: str | int,
        name: str,
        role: str,
        frame: np.ndarray,
        household_id: int | None = None,
    ) -> tuple[dict[str, Any], list[float]]:
        encoding = self.encode_single_face(frame)
        member = self.register_encoding(
            member_id, name, role, encoding, household_id=household_id
        )
        return member, encoding.astype(float).tolist()

    def process_frame(
        self,
        frame: np.ndarray,
        stream_id: str = "living_room",
        household_id: int | None = None,
        annotate: bool = True,
        persist_alert: bool = True,
    ) -> tuple[np.ndarray, dict[str, Any], list[dict[str, Any]]]:
        """Return annotated frame, presence snapshot, and FACE_UNKNOWN events."""
        if frame is None or frame.size == 0:
            raise ValueError("视频帧为空")
        face_recognition = _load_face_recognition()
        scale = self.resize_scale
        analysis = cv2.resize(frame, None, fx=scale, fy=scale) if scale != 1 else frame
        rgb = cv2.cvtColor(analysis, cv2.COLOR_BGR2RGB)
        locations = face_recognition.face_locations(rgb, model="hog")
        encodings = face_recognition.face_encodings(rgb, locations)

        with self._lock:
            candidates = [
                (member_id, deepcopy(member))
                for member_id, member in self._members.items()
                if household_id is None or member.get("household_id") == household_id
            ]
        known_ids = [item[0] for item in candidates]
        known_members = [item[1] for item in candidates]
        known_encodings = [np.asarray(item["encoding"]) for item in known_members]

        output = frame.copy() if annotate else frame
        faces: list[dict[str, Any]] = []
        members: list[dict[str, Any]] = []
        seen_members: set[str] = set()
        stranger_count = 0

        for track_id, (location, encoding) in enumerate(zip(locations, encodings)):
            matched_index = None
            distance = None
            if known_encodings:
                distances = face_recognition.face_distance(known_encodings, encoding)
                best = int(np.argmin(distances))
                distance = float(distances[best])
                if distance <= self.tolerance:
                    matched_index = best

            top, right, bottom, left = (int(round(value / scale)) for value in location)
            if matched_index is None:
                member_id, name, role, known = None, "Stranger", "stranger", False
                stranger_count += 1
                color = (0, 0, 255)
            else:
                member_id = known_ids[matched_index]
                registered = known_members[matched_index]
                name, role, known = registered["name"], registered["role"], True
                color = (0, 180, 0)
                if member_id not in seen_members:
                    members.append(
                        {"member_id": member_id, "name": name, "role": role}
                    )
                    seen_members.add(member_id)
            faces.append(
                {
                    "track_id": track_id,
                    "member_id": member_id,
                    "name": name,
                    "role": role,
                    "known": known,
                    "distance": round(distance, 4) if distance is not None else None,
                    "box": {"top": top, "right": right, "bottom": bottom, "left": left},
                }
            )
            if annotate:
                cv2.rectangle(output, (left, top), (right, bottom), color, 2)
                label = f"{member_id or 'Stranger'} ({role})"
                cv2.putText(
                    output, label, (left, max(20, top - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2, cv2.LINE_AA,
                )

        updated_at = datetime.now(timezone.utc).isoformat()
        presence = {
            "total": len(faces),
            "family": len(faces) - stranger_count,
            "stranger": stranger_count,
            "members": members,
            "faces": faces,
            "stream_id": str(stream_id),
            "updated_at": updated_at,
        }
        events: list[dict[str, Any]] = []
        now = datetime.now(timezone.utc).timestamp()
        last = self._last_unknown_alert.get(str(stream_id), 0.0)
        if stranger_count and now - last >= self.unknown_alert_cooldown:
            event = {
                "type": "FACE_UNKNOWN",
                "level": "HIGH",
                "stream_id": str(stream_id),
                "description": f"检测到 {stranger_count} 名陌生人",
                "detected_at": updated_at,
            }
            events.append(event)
            self._last_unknown_alert[str(stream_id)] = now
            if persist_alert:
                self._persist_unknown_alert(event, household_id)

        with self._lock:
            self._presence = deepcopy(presence)
        return output, presence, events

    @staticmethod
    def _persist_unknown_alert(event: dict[str, Any], household_id: int | None) -> None:
        try:
            from apps.alerts.services import create_alert

            create_alert(
                type=event["type"], level=event["level"],
                stream_id=event["stream_id"], description=event["description"],
                household_id=household_id,
            )
        except Exception:
            # The frame pipeline must keep running if the database is temporarily unavailable.
            import logging

            logging.getLogger(__name__).exception("Failed to persist FACE_UNKNOWN alert")

    def get_presence(self) -> dict[str, Any]:
        with self._lock:
            return deepcopy(self._presence)

    def list_registered_members(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                {
                    "member_id": member_id,
                    "name": member["name"],
                    "role": member["role"],
                    "household_id": member.get("household_id"),
                }
                for member_id, member in self._members.items()
            ]


_service: FaceRecognitionService | None = None
_service_lock = threading.Lock()


def get_face_service() -> FaceRecognitionService:
    global _service
    if _service is None:
        with _service_lock:
            if _service is None:
                _service = FaceRecognitionService()
    return _service
