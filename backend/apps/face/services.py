"""Face detection, 128-d encoding, matching, and presence statistics."""

from __future__ import annotations

import base64
import json
import logging
import os
import threading
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def _member_display_name(member: dict[str, Any]) -> str:
    identity = str(member.get("identity") or "").strip()
    if identity:
        return identity
    return str(member.get("name") or "").strip()


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
        self._last_db_sync = 0.0
        self._presence_by_stream: dict[str, dict[str, Any]] = {}
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
                "identity": str(member.get("identity") or ""),
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

    def sync_members_from_database(self, force: bool = False) -> None:
        """从 FamilyMember.face_encoding 刷新内存中的人脸特征库。"""
        try:
            from django.conf import settings

            refresh_seconds = float(
                getattr(settings, "FACE_DB_REFRESH_SECONDS", 10)
            )
        except Exception:
            refresh_seconds = 10.0

        now = time.time()
        if not force and now - self._last_db_sync < refresh_seconds:
            return

        try:
            from apps.accounts.models import FamilyMember

            rows = FamilyMember.objects.filter(
                is_active=True,
                face_encoding__isnull=False,
            ).values("id", "name", "identity", "role", "household_id", "face_encoding")

            members: dict[str, dict[str, Any]] = {}
            for row in rows:
                encoding = row.get("face_encoding") or []
                if len(encoding) != 128:
                    continue
                member_id = str(row["id"])
                members[member_id] = {
                    "name": str(row.get("name") or member_id),
                    "identity": str(row.get("identity") or ""),
                    "role": str(row.get("role") or "adult"),
                    "household_id": row.get("household_id"),
                    "encoding": [float(value) for value in encoding],
                }

            with self._lock:
                if members:
                    self._members = members
                    self._save_registry()
                self._last_db_sync = now
        except Exception as exc:
            self._last_db_sync = now
            if "no such table" in str(exc).lower():
                logger.debug("人脸特征库数据表尚未就绪: %s", exc)
            else:
                logger.warning("从数据库同步人脸特征库失败: %s", exc)
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
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        with self._lock:
            face_recognition = _load_face_recognition()
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
        identity: str = "",
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
                "identity": str(identity or "").strip(),
                "role": str(role).strip(),
                "household_id": household_id,
                "encoding": values.astype(float).tolist(),
            }
            self._save_registry()
        display_name = _member_display_name(self._members[member_id])
        return {
            "member_id": member_id,
            "name": display_name,
            "real_name": str(name).strip(),
            "identity": str(identity or "").strip(),
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

    @staticmethod
    def draw_face_boxes(frame: np.ndarray, presence: dict[str, Any]) -> np.ndarray:
        """根据 presence 中的人脸坐标在 BGR 帧上绘制标注框。"""
        if frame is None or frame.size == 0:
            return frame

        output = frame.copy()
        height, width = output.shape[:2]
        for face in presence.get("faces", []):
            box = face.get("box") or {}
            left = int(box.get("left", 0))
            top = int(box.get("top", 0))
            right = int(box.get("right", 0))
            bottom = int(box.get("bottom", 0))
            if right <= left or bottom <= top:
                continue

            left = max(0, min(left, width - 1))
            top = max(0, min(top, height - 1))
            right = max(left + 1, min(right, width))
            bottom = max(top + 1, min(bottom, height))

            known = bool(face.get("known"))
            trusted = face.get("trusted", True) is not False
            color = (0, 165, 255) if not trusted else ((0, 180, 0) if known else (0, 0, 255))
            name = str(face.get("name") or "").strip()
            role = str(face.get("role") or "").strip()
            if not trusted:
                label = "spoof suspected"
                cv2.rectangle(output, (left, top), (right, bottom), color, 2)
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
                continue
            if not known:
                label = "陌生人"
            else:
                role_labels = {"adult": "成人", "child": "儿童"}
                role_text = role_labels.get(role, role or "家人")
                label = f"{name or '家人'} ({role_text})"

            cv2.rectangle(output, (left, top), (right, bottom), color, 2)
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
        return output

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
        self.sync_members_from_database()
        scale = self.resize_scale
        analysis = cv2.resize(frame, None, fx=scale, fy=scale) if scale != 1 else frame
        rgb = cv2.cvtColor(analysis, cv2.COLOR_BGR2RGB)

        # dlib/face_recognition 不是线程安全的；多路视频 worker 共享单例时必须串行。
        with self._lock:
            face_recognition = _load_face_recognition()
            candidates = [
                (member_id, deepcopy(member))
                for member_id, member in self._members.items()
                if household_id is None or member.get("household_id") == household_id
            ]
            known_ids = [item[0] for item in candidates]
            known_members = [item[1] for item in candidates]
            known_encodings = [np.asarray(item["encoding"]) for item in known_members]
            locations = face_recognition.face_locations(rgb, model="hog")
            encodings = face_recognition.face_encodings(rgb, locations)

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

                top, right, bottom, left = (
                    int(round(value / scale)) for value in location
                )
                real_name = None
                identity = ""
                if matched_index is None:
                    member_id, name, role, known = None, "Stranger", "stranger", False
                    stranger_count += 1
                else:
                    member_id = known_ids[matched_index]
                    registered = known_members[matched_index]
                    real_name = registered["name"]
                    identity = str(registered.get("identity") or "").strip()
                    display_name = _member_display_name(registered)
                    name, role, known = display_name, registered["role"], True
                    if member_id not in seen_members:
                        members.append(
                            {
                                "member_id": member_id,
                                "name": display_name,
                                "real_name": real_name,
                                "identity": identity,
                                "role": role,
                            }
                        )
                        seen_members.add(member_id)
                faces.append(
                    {
                        "track_id": track_id,
                        "member_id": member_id,
                        "name": name,
                        "real_name": real_name,
                        "identity": identity,
                        "role": role,
                        "known": known,
                        "distance": round(distance, 4) if distance is not None else None,
                        "box": {
                            "top": top,
                            "right": right,
                            "bottom": bottom,
                            "left": left,
                        },
                    }
                )

        output = frame.copy() if annotate else frame

        updated_at = datetime.now(timezone.utc).isoformat()
        height, width = frame.shape[:2]
        presence = {
            "total": len(faces),
            "family": len(faces) - stranger_count,
            "stranger": stranger_count,
            "members": members,
            "faces": faces,
            "stream_id": str(stream_id),
            "frame_size": {"width": int(width), "height": int(height)},
            "updated_at": updated_at,
        }
        if annotate and faces:
            output = self.draw_face_boxes(frame, presence)
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
            if persist_alert:
                persisted = self._persist_unknown_alert(
                    event, household_id, frame=output
                )
                if persisted:
                    self._last_unknown_alert[str(stream_id)] = now
            else:
                self._last_unknown_alert[str(stream_id)] = now

        with self._lock:
            self._presence_by_stream[str(stream_id)] = deepcopy(presence)
        return output, presence, events

    @staticmethod
    def _persist_unknown_alert(
        event: dict[str, Any],
        household_id: int | None,
        frame: np.ndarray | None = None,
    ) -> bool:
        if household_id is None:
            logger.warning(
                "Skipping unscoped FACE_UNKNOWN alert for stream %s; will retry",
                event.get("stream_id"),
            )
            return False
        try:
            from apps.alerts.services import create_alert

            create_alert(
                type=event["type"],
                level=event["level"],
                stream_id=event["stream_id"],
                description=event["description"],
                household_id=household_id,
                frame=frame,
            )
            return True
        except Exception:
            # 数据库临时不可用时，视频帧处理链仍要继续运行。
            logger.exception("持久化 FACE_UNKNOWN 告警失败")
            return False

    def get_presence(self, stream_id: str | None = None) -> dict[str, Any]:
        with self._lock:
            if stream_id:
                return deepcopy(
                    self._presence_by_stream.get(
                        str(stream_id), self._empty_presence()
                    )
                )
            if not self._presence_by_stream:
                return self._empty_presence()
            latest = max(
                self._presence_by_stream.values(),
                key=lambda item: item.get("updated_at") or "",
            )
            return deepcopy(latest)

    def get_all_presence(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return deepcopy(self._presence_by_stream)

    def set_presence(self, presence: dict[str, Any]) -> None:
        with self._lock:
            stream_id = presence.get("stream_id")
            if stream_id:
                self._presence_by_stream[str(stream_id)] = deepcopy(presence)

    def list_registered_members(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                {
                    "member_id": member_id,
                    "name": _member_display_name(member),
                    "real_name": member["name"],
                    "identity": str(member.get("identity") or ""),
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
