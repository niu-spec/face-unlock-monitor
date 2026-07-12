import logging
import os
import re
import threading
import time

import cv2
import numpy as np

logger = logging.getLogger(__name__)


RTSP_BASE_URL = os.getenv("RTSP_BASE_URL", "rtsp://127.0.0.1:8554/stream")
RTMP_PUBLIC_BASE_URL = os.getenv(
    "RTMP_PUBLIC_BASE_URL", "rtmp://152.136.29.158:9090/stream"
)
FRAME_SKIP = int(os.getenv("VIDEO_FRAME_SKIP", "5"))
JPEG_QUALITY = max(40, min(95, int(os.getenv("VIDEO_JPEG_QUALITY", "80"))))
CAPTURE_BUFFER_SIZE = max(1, int(os.getenv("VIDEO_CAPTURE_BUFFER_SIZE", "1")))
METADATA_CACHE_SECONDS = max(
    0.0, float(os.getenv("VIDEO_METADATA_CACHE_SECONDS", "5"))
)
PRESENCE_STALE_SECONDS = max(
    1.0, float(os.getenv("PRESENCE_STALE_SECONDS", "5"))
)
SHOW_VIDEO_HUD = os.getenv("VIDEO_SHOW_HUD", "").lower() in ("1", "true", "yes")
STREAM_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")

workers = {}
workers_lock = threading.Lock()
liveness_snapshots = {}
liveness_lock = threading.Lock()
metadata_cache_lock = threading.Lock()
household_id_cache = {}
zones_cache = {}


def build_rtsp_url(stream_id):
    return f"{RTSP_BASE_URL.rstrip('/')}/{stream_id}"


def build_public_rtmp_url(stream_id):
    return f"{RTMP_PUBLIC_BASE_URL.rstrip('/')}/{stream_id}"


# 视频层 → 业务层 stream_id 映射（OpenSpec config.yaml 双轨约定）
_VIDEO_TO_BUSINESS_STREAM = {
    "1": "living_room",
    "2": "kitchen",
}
_BUSINESS_TO_VIDEO_STREAM = {v: k for k, v in _VIDEO_TO_BUSINESS_STREAM.items()}


def _to_business_stream_id(stream_id: str) -> str:
    """将视频层 ID (1/2) 转换为业务层 ID (living_room/kitchen)。"""
    return _VIDEO_TO_BUSINESS_STREAM.get(stream_id, stream_id)


def resolve_presence_stream_id(stream_id: str | None) -> str | None:
    """解析 presence 查询参数中的 stream_id。"""
    raw = (stream_id or "").strip()
    if not raw:
        return None
    return _to_business_stream_id(raw)


def resolve_video_stream_id(stream_id: str | None) -> str | None:
    """将查询参数解析为视频层 stream_id（1/2），供 RTSP worker 使用。"""
    raw = (stream_id or "").strip()
    if not raw:
        return None
    if raw in _VIDEO_TO_BUSINESS_STREAM:
        return raw
    return _BUSINESS_TO_VIDEO_STREAM.get(raw)


def ensure_worker_for_query(stream_id: str | None) -> None:
    """前端轮询 status 时拉起 RTSP worker，无需打开 MJPEG 预览。"""
    video_stream_id = resolve_video_stream_id(stream_id)
    if not video_stream_id or not STREAM_ID_PATTERN.match(video_stream_id):
        return
    get_worker(video_stream_id)


def _worker_timestamp_is_stale(timestamp: float | None) -> bool:
    if timestamp is None:
        return True
    return (time.time() - float(timestamp)) > PRESENCE_STALE_SECONDS


def worker_stream_is_live(worker: dict | None) -> bool:
    """RTSP 采集仍在更新则视为有推流（与 AI 处理耗时解耦）。"""
    if not worker:
        return False
    return not _worker_timestamp_is_stale(worker.get("last_capture_at"))


def worker_detection_is_lagging(worker: dict | None) -> bool:
    """AI 处理完成时间过旧，检测/人数数据可能滞后于画面。"""
    if not worker:
        return True
    return _worker_timestamp_is_stale(worker.get("last_frame_at"))


def worker_presence_is_stale(worker: dict | None) -> bool:
    """推流是否已停止（用于清空 presence 与 stream_live）。"""
    return not worker_stream_is_live(worker)


def resolve_presence_payload(
    service,
    biz_stream_id: str | None,
    worker: dict | None,
) -> tuple[dict, bool]:
    """返回 presence 与 stream_live；停推流后清空过期检测数据。"""
    from apps.face.services import FaceRecognitionService

    if not worker_stream_is_live(worker):
        presence = FaceRecognitionService._empty_presence()
        if biz_stream_id:
            presence["stream_id"] = biz_stream_id
        return presence, False

    presence = service.get_presence(biz_stream_id)
    return presence, True


def resolve_household_id_for_stream(stream_id: str) -> int | None:
    """尽力根据业务流 ID 找到对应家庭 ID。"""
    return _resolve_household_id_for_stream(stream_id)


def _resolve_household_id_for_stream(stream_id: str) -> int | None:
    """尽力根据业务流 ID 找到对应家庭 ID。"""
    now = time.monotonic()
    with metadata_cache_lock:
        cached = household_id_cache.get(stream_id)
        if cached is not None and cached[0] > now:
            return cached[1]

    try:
        from apps.households.models import Camera

        household_id = Camera.objects.filter(
            stream_id=stream_id,
            is_active=True,
            household_id__isnull=False,
        ).values_list("household_id", flat=True).first()
        with metadata_cache_lock:
            household_id_cache[stream_id] = (
                now + METADATA_CACHE_SECONDS,
                household_id,
            )
        return household_id
    except Exception as exc:
        logger.warning("根据视频流 %s 查询家庭失败: %s", stream_id, exc)
        return None


def _get_active_zones(stream_id: str, household_id: int | None) -> list[dict]:
    """Return active zone metadata with a short TTL to avoid per-frame SQL."""
    cache_key = (stream_id, household_id)
    now = time.monotonic()
    with metadata_cache_lock:
        cached = zones_cache.get(cache_key)
        if cached is not None and cached[0] > now:
            return [dict(zone) for zone in cached[1]]

    from apps.zones.models import Zone

    zones_qs = Zone.objects.filter(stream_id=stream_id, is_active=True)
    if household_id is not None:
        zones_qs = zones_qs.filter(household_id=household_id)
    zones = [
        {
            "id": zone.id,
            "name": zone.name,
            "points_json": zone.points_json,
            "forbidden_roles": zone.forbidden_roles,
            "safe_distance": zone.safe_distance,
            "dwell_time": zone.dwell_time,
            "is_active": zone.is_active,
        }
        for zone in zones_qs
    ]
    with metadata_cache_lock:
        zones_cache[cache_key] = (now + METADATA_CACHE_SECONDS, zones)
    return [dict(zone) for zone in zones]


def clear_zone_metadata_cache() -> None:
    """区域增删改后立即使视频管线重新加载配置。"""
    with metadata_cache_lock:
        zones_cache.clear()


def _person_boxes_from_faces(presence: dict, person_boxes: list[dict]) -> list[dict]:
    """HOG/YOLO 未检出人体时，用人脸框作为区域检测的降级输入。"""
    if person_boxes:
        return person_boxes

    boxes: list[dict] = []
    for index, face in enumerate(presence.get("faces") or []):
        box = face.get("box") or {}
        left = int(box.get("left", 0))
        top = int(box.get("top", 0))
        right = int(box.get("right", 0))
        bottom = int(box.get("bottom", 0))
        if right <= left or bottom <= top:
            continue
        boxes.append(
            {
                "x": left,
                "y": top,
                "w": right - left,
                "h": bottom - top,
                "track_id": int(face.get("track_id", index)),
            }
        )
    return boxes


def _map_face_roles_to_people(presence: dict, person_boxes: list[dict]) -> dict[int, str]:
    """通过人脸中心点是否落入人体框，将人脸角色关联到人体框。"""
    roles: dict[int, str] = {}
    for face in presence.get("faces", []):
        box = face.get("box") or {}
        if not box:
            continue
        cx = (int(box.get("left", 0)) + int(box.get("right", 0))) // 2
        cy = (int(box.get("top", 0)) + int(box.get("bottom", 0))) // 2
        matched = False
        for person in person_boxes:
            x, y, w, h = person["x"], person["y"], person["w"], person["h"]
            if x <= cx <= x + w and y <= cy <= y + h:
                roles[int(person.get("track_id", -1))] = face.get("role", "stranger")
                matched = True
                break
        if not matched:
            track_id = int(face.get("track_id", len(roles)))
            roles[track_id] = face.get("role", "stranger")
    return roles


ALERT_OVERLAY_TTL_SEC = 3.0
CANVAS_ALERT_TYPES = frozenset({"FIRE", "FALL", "INTRUSION", "PROXIMITY", "LOITER"})


def _face_overlay_snapshot(presence: dict) -> list[dict]:
    """Build a JSON-safe face-box snapshot for the browser canvas overlay."""
    overlays: list[dict] = []
    for index, face in enumerate(presence.get("faces") or []):
        box = face.get("box") or {}
        left = int(box.get("left", 0))
        top = int(box.get("top", 0))
        right = int(box.get("right", 0))
        bottom = int(box.get("bottom", 0))
        width = right - left
        height = bottom - top
        if width <= 0 or height <= 0:
            continue
        overlays.append(
            {
                "x": left,
                "y": top,
                "w": width,
                "h": height,
                "track_id": int(face.get("track_id", index)),
                "known": bool(face.get("known")),
                "name": face.get("name"),
                "role": face.get("role"),
                "trusted": face.get("trusted", True),
            }
        )
    return overlays


def _alert_overlay_snapshot(results: list[dict]) -> list[dict]:
    """Extract fire/fall bounding boxes from detection results for canvas overlay."""
    overlays: list[dict] = []
    for result in results:
        alert_type = str(result.get("alert_type", ""))
        if alert_type not in CANVAS_ALERT_TYPES:
            continue
        bbox = result.get("bbox")
        if not bbox or len(bbox) != 4:
            continue
        x, y, width, height = (int(value) for value in bbox)
        if width <= 0 or height <= 0:
            continue
        item = {
            "x": x,
            "y": y,
            "w": width,
            "h": height,
            "alert_type": alert_type,
            "severity": result.get("severity", "high"),
        }
        message = result.get("message")
        if message:
            item["message"] = str(message)
        overlays.append(item)
    return overlays


def _resolve_alert_overlay_boxes(
    previous_presence: dict,
    results: list[dict],
    *,
    now: float | None = None,
) -> tuple[list[dict], float | None]:
    """Keep alert boxes visible briefly so fast frontend polling can still catch them."""
    current = _alert_overlay_snapshot(results)
    if current:
        timestamp = now if now is not None else time.time()
        return current, timestamp

    previous_boxes = previous_presence.get("alert_boxes") or []
    previous_at = previous_presence.get("alert_boxes_updated_at")
    if (
        previous_boxes
        and previous_at is not None
        and (now if now is not None else time.time()) - float(previous_at)
        < ALERT_OVERLAY_TTL_SEC
    ):
        return previous_boxes, float(previous_at)
    return [], None


def _apply_alert_overlay_presence(
    presence: dict,
    previous_presence: dict,
    results: list[dict],
) -> None:
    alert_boxes, alert_boxes_updated_at = _resolve_alert_overlay_boxes(
        previous_presence,
        results,
    )
    presence["alert_boxes"] = alert_boxes
    if alert_boxes_updated_at is not None:
        presence["alert_boxes_updated_at"] = alert_boxes_updated_at
    else:
        presence.pop("alert_boxes_updated_at", None)


def _person_overlay_snapshot(presence: dict, person_boxes: list[dict]) -> list[dict]:
    """Build a JSON-safe person-box snapshot for the browser canvas overlay."""
    overlays: list[dict] = []
    faces = presence.get("faces") or []
    for person in person_boxes:
        x = int(person.get("x", 0))
        y = int(person.get("y", 0))
        width = int(person.get("w", 0))
        height = int(person.get("h", 0))
        if width <= 0 or height <= 0:
            continue

        item = {
            "x": x,
            "y": y,
            "w": width,
            "h": height,
            "track_id": int(person.get("track_id", len(overlays))),
        }
        confidence = person.get("confidence")
        if confidence is not None:
            item["confidence"] = round(float(confidence), 3)

        for face in faces:
            box = face.get("box") or {}
            face_x = (int(box.get("left", 0)) + int(box.get("right", 0))) // 2
            face_y = (int(box.get("top", 0)) + int(box.get("bottom", 0))) // 2
            if x <= face_x <= x + width and y <= face_y <= y + height:
                item.update(
                    {
                        "known": bool(face.get("known")),
                        "name": face.get("name"),
                        "role": face.get("role"),
                        "trusted": face.get("trusted", True),
                    }
                )
                break
        overlays.append(item)
    return overlays


def _update_liveness_snapshot(stream_id: str, liveness: dict) -> None:
    with liveness_lock:
        liveness_snapshots[str(stream_id)] = {
            "stream_id": str(stream_id),
            "updated_at": time.time(),
            "passed": bool(liveness.get("passed")),
            "status": liveness.get("status", "unknown"),
            "attack_type": liveness.get("attack_type"),
            "score": liveness.get("score"),
            "reason": liveness.get("reason", ""),
            "details": liveness.get("details", {}),
        }


def get_liveness_status():
    with liveness_lock:
        return {stream_id: dict(value) for stream_id, value in liveness_snapshots.items()}


def _mark_faces_untrusted(presence: dict, liveness: dict) -> None:
    if liveness.get("status") != "attack":
        return
    for face in presence.get("faces") or []:
        face["trusted"] = False
        face["spoof_attack_type"] = liveness.get("attack_type")
        face["spoof_reason"] = liveness.get("reason", "")


def process_frame(
    frame,
    stream_id,
    *,
    frame_captured_at: float | None = None,
    frame_sequence: int | None = None,
):
    """在 MJPEG 编码前执行实时 AI 处理链。"""
    try:
        from django.db import close_old_connections

        close_old_connections()
    except Exception:
        pass

    biz_stream_id = _to_business_stream_id(str(stream_id))
    original = frame.copy()
    output = frame
    person_boxes: list[dict] = []
    face_roles: dict[int, str] = {}
    zones = None
    face_count = 0
    ai_ok = False
    presence: dict = {}
    liveness: dict = {}

    try:
        from apps.detection.services import get_detection_service
        from apps.face.liveness import get_liveness_service
        from apps.face.services import get_face_service

        household_id = _resolve_household_id_for_stream(biz_stream_id)
        face_service = get_face_service()
        detection_service = get_detection_service()
        previous_presence = face_service.get_presence(biz_stream_id)
        previous_persons = previous_presence.get("persons", [])
        previous_face_boxes = previous_presence.get("face_boxes", [])
        fast_results: list[dict] = []
        output, presence, _events = face_service.process_frame(
            original,
            stream_id=biz_stream_id,
            household_id=household_id,
            annotate=True,
            persist_alert=True,
        )
        # Fast path 1/3: publish face boxes before YOLO/liveness/zone stages.
        if frame_captured_at is not None:
            presence["frame_captured_at"] = frame_captured_at
        if frame_sequence is not None:
            presence["frame_sequence"] = frame_sequence
        presence["persons"] = previous_persons
        presence["face_boxes"] = _face_overlay_snapshot(presence) or previous_face_boxes
        _apply_alert_overlay_presence(presence, previous_presence, [])
        face_service.set_presence(presence)

        # Fast path 2/3: fire detection only needs the frame, run before YOLO.
        fire_results = detection_service.detect_fire_alerts(
            original,
            biz_stream_id,
            household_id=household_id,
            snapshot_frame=output,
        )
        fast_results.extend(fire_results)
        presence["face_boxes"] = _face_overlay_snapshot(presence) or previous_face_boxes
        _apply_alert_overlay_presence(presence, previous_presence, fast_results)
        face_service.set_presence(presence)

        person_boxes = detection_service.detect_people(original)
        person_boxes = _person_boxes_from_faces(presence, person_boxes)
        face_roles = _map_face_roles_to_people(presence, person_boxes)

        fall_results = detection_service.detect_fall_alerts(
            person_boxes,
            biz_stream_id,
            household_id=household_id,
            snapshot_frame=output,
        )
        fast_results.extend(fall_results)
        if fast_results:
            detection_service.enqueue_detection_results(biz_stream_id, fast_results)

        # Fast path 3/3: publish person + face + fire/fall overlays before liveness.
        presence["persons"] = _person_overlay_snapshot(presence, person_boxes)
        presence["face_boxes"] = _face_overlay_snapshot(presence)
        _apply_alert_overlay_presence(presence, previous_presence, fast_results)
        face_service.set_presence(presence)

        liveness, _liveness_events = get_liveness_service().observe(
            original,
            presence,
            stream_id=biz_stream_id,
            household_id=household_id,
            persist_alert=True,
        )
        _mark_faces_untrusted(presence, liveness)
        presence["face_boxes"] = _face_overlay_snapshot(presence)
        # Liveness only updates face trust labels; keep fast-path person/alert boxes.
        face_service.set_presence(presence)
        _update_liveness_snapshot(biz_stream_id, liveness)

        zones = _get_active_zones(biz_stream_id, household_id)

        slow_results = detection_service.process_frame(
            frame=original,
            stream_id=biz_stream_id,
            person_boxes=person_boxes,
            face_roles=face_roles,
            zones=zones if zones else None,
            snapshot_frame=output,
            household_id=household_id,
            include_fast=False,
        )
        results = fast_results + slow_results
        zone_overlay_results = [
            result
            for result in slow_results
            if str(result.get("alert_type", "")) in CANVAS_ALERT_TYPES
        ]
        if zone_overlay_results:
            _apply_alert_overlay_presence(
                presence,
                previous_presence,
                fast_results + zone_overlay_results,
            )
            face_service.set_presence(presence)
        face_count = len(presence.get("faces", []))
        output = detection_service.draw_overlays(
            output,
            results,
            zones=zones if zones else None,
            # 已检测到人脸时不画黄色人体框，避免与绿/红人脸框重叠
            person_boxes=[] if face_count else person_boxes,
        )
        # 保底：D 组 draw_overlays 可能覆盖人脸层，最终由 C 组统一重绘人脸框
        if face_count:
            output = face_service.draw_face_boxes(output, presence)
        ai_ok = True
    except Exception as exc:
        logger.warning(
            "视频流 %s 的 AI 处理链执行失败: %s",
            stream_id,
            exc,
            exc_info=True,
        )

    if ai_ok:
        live_status = liveness.get("status", "unknown") if liveness else "unknown"
        attack_type = liveness.get("attack_type") if liveness else None
        attack_hint = f" attack:{attack_type}" if attack_type else ""
        ai_status = (
            f"faces:{face_count}  persons:{len(person_boxes)}  "
            f"live:{live_status}{attack_hint}"
        )
    else:
        ai_status = "AI err"
    if SHOW_VIDEO_HUD:
        cv2.putText(
            output,
            f"stream {stream_id}",
            (12, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )
        cv2.putText(
            output,
            ai_status,
            (12, 52),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 255, 255) if ai_ok else (0, 0, 255),
            1,
            cv2.LINE_AA,
        )
    return output
def encode_frame(frame):
    ok, buffer = cv2.imencode(
        ".jpg",
        frame,
        [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY],
    )
    if not ok:
        return None
    return buffer.tobytes()


def multipart_frame(jpeg_bytes):
    return (
        b"--frame\r\n"
        b"Content-Type: image/jpeg\r\n\r\n" + jpeg_bytes + b"\r\n"
    )


def placeholder_frame(message):
    frame = np.zeros((480, 720, 3), dtype=np.uint8)
    cv2.putText(
        frame,
        message,
        (40, 240),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    return frame


class CameraWorker:
    def __init__(self, stream_id, frame_skip=FRAME_SKIP):
        self.stream_id = stream_id
        self.stream_url = build_rtsp_url(stream_id)
        self.frame_skip = max(1, frame_skip)
        self.latest_frame = None
        self.latest_jpeg = None
        self.last_error = None
        self.last_process_error = None
        self.last_capture_at = None
        self.last_frame_at = None
        self.last_process_duration = None
        self.running = False
        self._condition = threading.Condition()
        self._capture_thread = None
        self._process_thread = None
        self._raw_frame = None
        self._raw_frame_captured_at = None
        self._capture_sequence = 0
        self._processed_version = 0
        self._processed_input_sequence = 0
        self._dropped_stale_frames = 0
        self._recent_process_times = []

    def start(self):
        if self.running:
            return
        self.running = True
        self._capture_thread = threading.Thread(
            target=self._capture_loop,
            daemon=True,
            name=f"camera-capture-{self.stream_id}",
        )
        self._process_thread = threading.Thread(
            target=self._process_loop,
            daemon=True,
            name=f"camera-ai-{self.stream_id}",
        )
        self._capture_thread.start()
        self._process_thread.start()

    def _capture_loop(self):
        """Continuously drain RTSP and retain only the newest raw frame.

        AI inference deliberately runs in another thread.  If inference is
        slower than the camera, replacing ``_raw_frame`` drops stale frames
        instead of allowing OpenCV/FFmpeg's RTSP buffer to grow indefinitely.
        """
        while self.running:
            capture = cv2.VideoCapture(self.stream_url)
            capture.set(cv2.CAP_PROP_BUFFERSIZE, CAPTURE_BUFFER_SIZE)
            if not capture.isOpened():
                with self._condition:
                    self.last_error = "RTSP stream not available"
                time.sleep(1)
                continue

            with self._condition:
                self.last_error = None
            try:
                while self.running:
                    ok, frame = capture.read()
                    if not ok:
                        with self._condition:
                            self.last_error = "failed to read frame"
                        time.sleep(0.2)
                        break

                    now = time.time()
                    with self._condition:
                        # Detach from OpenCV's internal RTSP buffer before the next
                        # capture.read() can reuse or free the underlying memory.
                        self._raw_frame = frame.copy()
                        self._raw_frame_captured_at = now
                        self._capture_sequence += 1
                        self.last_capture_at = now
                        self._condition.notify_all()
            finally:
                capture.release()

    def _process_loop(self):
        """Run AI against the newest frame without blocking RTSP capture."""
        last_input_sequence = 0
        while self.running:
            with self._condition:
                self._condition.wait_for(
                    lambda: (
                        not self.running
                        or self._capture_sequence - last_input_sequence
                        >= self.frame_skip
                    ),
                    timeout=1.0,
                )
                if not self.running:
                    return
                if self._raw_frame is None:
                    continue
                frame = self._raw_frame.copy()
                frame_captured_at = self._raw_frame_captured_at
                input_sequence = self._capture_sequence

            started_at = time.perf_counter()
            try:
                processed_frame = process_frame(
                    frame,
                    self.stream_id,
                    frame_captured_at=frame_captured_at,
                    frame_sequence=input_sequence,
                )
                jpeg_bytes = encode_frame(processed_frame)
                if jpeg_bytes is None:
                    raise RuntimeError("failed to encode processed frame")
            except Exception as exc:
                logger.warning(
                    "视频流 %s 的异步 AI 处理失败: %s",
                    self.stream_id,
                    exc,
                    exc_info=True,
                )
                with self._condition:
                    self.last_process_error = str(exc)
                last_input_sequence = input_sequence
                continue

            finished_at = time.time()
            process_duration = time.perf_counter() - started_at
            stale_frames = max(0, input_sequence - last_input_sequence - 1)
            with self._condition:
                self.latest_frame = processed_frame
                self.latest_jpeg = jpeg_bytes
                self.last_frame_at = finished_at
                self.last_process_duration = process_duration
                self.last_process_error = None
                self._processed_version += 1
                self._processed_input_sequence = input_sequence
                self._dropped_stale_frames += stale_frames
                self._recent_process_times.append(finished_at)
                if len(self._recent_process_times) > 20:
                    self._recent_process_times.pop(0)
                self._condition.notify_all()
            last_input_sequence = input_sequence

    def get_latest_frame(self):
        with self._condition:
            if self.latest_frame is None:
                return None
            return self.latest_frame.copy()

    def wait_for_jpeg(self, after_version=-1, timeout=1.0):
        """Wait for a newly processed JPEG and return ``(bytes, version)``."""
        with self._condition:
            self._condition.wait_for(
                lambda: (
                    not self.running
                    or (
                        self.latest_jpeg is not None
                        and self._processed_version != after_version
                    )
                ),
                timeout=timeout,
            )
            return self.latest_jpeg, self._processed_version

    def to_status(self):
        with self._condition:
            process_fps = 0.0
            if len(self._recent_process_times) >= 2:
                elapsed = self._recent_process_times[-1] - self._recent_process_times[0]
                if elapsed > 0:
                    process_fps = (len(self._recent_process_times) - 1) / elapsed
            return {
                "stream_url": self.stream_url,
                "status": "running" if self.running else "stopped",
                "has_frame": self.latest_frame is not None,
                "last_capture_at": self.last_capture_at,
                "last_frame_at": self.last_frame_at,
                "last_process_duration_ms": (
                    round(self.last_process_duration * 1000, 1)
                    if self.last_process_duration is not None
                    else None
                ),
                "process_fps": round(process_fps, 2),
                "captured_sequence": self._capture_sequence,
                "processed_sequence": self._processed_input_sequence,
                "dropped_stale_frames": self._dropped_stale_frames,
                "last_error": self.last_error,
                "last_process_error": self.last_process_error,
            }


def get_worker(stream_id):
    with workers_lock:
        worker = workers.get(stream_id)
        if worker is None:
            worker = CameraWorker(stream_id)
            workers[stream_id] = worker
        worker.start()
    # ★ v1.3 音频检测：为每个视频流启动音频采集（锁外执行，避免阻塞）
    _start_audio_for_stream(stream_id)
    return worker


def _start_audio_for_stream(stream_id: str):
    """为指定视频流启动音频异常检测（v1.3）。

    仅在音频模型可加载且 RTSP 含音频轨道时生效。
    RTSP 无音频时自动降级，不影响视频检测。
    """
    try:
        from apps.detection.audio_service import get_audio_service
        from apps.detection.av_correlation import get_av_correlation_buffer

        # 先初始化联动缓冲器
        av_buffer = get_av_correlation_buffer()

        # 获取或创建音频服务（注入联动缓冲器）
        audio_svc = get_audio_service(av_correlation_buffer=av_buffer)

        # 检查是否已为此流启动
        if stream_id in audio_svc._captures:
            return

        rtsp_url = build_rtsp_url(stream_id)
        audio_svc.start_for_stream(
            stream_id=_to_business_stream_id(str(stream_id)),
            rtsp_url=rtsp_url,
        )
    except Exception as e:
        logger.info("音频检测启动跳过 (stream=%s): %s", stream_id, e)


def get_workers_status():
    return {
        stream_id: worker.to_status()
        for stream_id, worker in workers.items()
    }


def gen_frames(stream_id):
    worker = get_worker(stream_id)
    empty_frame = placeholder_frame("waiting for RTSP frame")
    empty_jpeg = encode_frame(empty_frame)
    last_version = -1
    last_placeholder_at = 0.0

    while True:
        jpeg_bytes, version = worker.wait_for_jpeg(last_version, timeout=1.0)
        if jpeg_bytes is not None and version != last_version:
            yield multipart_frame(jpeg_bytes)
            last_version = version
            continue

        # Keep the HTTP stream alive while RTSP has not produced its first
        # processed frame.  Once frames are flowing, do not resend duplicates.
        now = time.time()
        if last_version < 0 and empty_jpeg and now - last_placeholder_at >= 1.0:
            yield multipart_frame(empty_jpeg)
            last_placeholder_at = now
