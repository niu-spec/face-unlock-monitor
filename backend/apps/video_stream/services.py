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
SHOW_VIDEO_HUD = os.getenv("VIDEO_SHOW_HUD", "").lower() in ("1", "true", "yes")
STREAM_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")

workers = {}
workers_lock = threading.Lock()


def build_rtsp_url(stream_id):
    return f"{RTSP_BASE_URL.rstrip('/')}/{stream_id}"


def build_public_rtmp_url(stream_id):
    return f"{RTMP_PUBLIC_BASE_URL.rstrip('/')}/{stream_id}"


# 视频层 → 业务层 stream_id 映射（OpenSpec config.yaml 双轨约定）
_VIDEO_TO_BUSINESS_STREAM = {
    "1": "living_room",
    "2": "kitchen",
}


def _to_business_stream_id(stream_id: str) -> str:
    """将视频层 ID (1/2) 转换为业务层 ID (living_room/kitchen)。"""
    return _VIDEO_TO_BUSINESS_STREAM.get(stream_id, stream_id)


def _resolve_household_id_for_stream(stream_id: str) -> int | None:
    """尽力根据业务流 ID 找到对应家庭 ID。"""
    try:
        from apps.households.models import Camera

        return Camera.objects.filter(
            stream_id=stream_id,
            is_active=True,
            household_id__isnull=False,
        ).values_list("household_id", flat=True).first()
    except Exception as exc:
        logger.warning("根据视频流 %s 查询家庭失败: %s", stream_id, exc)
        return None


def _map_face_roles_to_people(presence: dict, person_boxes: list[dict]) -> dict[int, str]:
    """通过人脸中心点是否落入人体框，将人脸角色关联到人体框。"""
    roles: dict[int, str] = {}
    for face in presence.get("faces", []):
        box = face.get("box") or {}
        if not box:
            continue
        cx = (int(box.get("left", 0)) + int(box.get("right", 0))) // 2
        cy = (int(box.get("top", 0)) + int(box.get("bottom", 0))) // 2
        for person in person_boxes:
            x, y, w, h = person["x"], person["y"], person["w"], person["h"]
            if x <= cx <= x + w and y <= cy <= y + h:
                roles[int(person.get("track_id", -1))] = face.get("role", "stranger")
                break
    return roles


def process_frame(frame, stream_id):
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

    try:
        from apps.detection.services import get_detection_service
        from apps.face.services import get_face_service
        from apps.zones.models import Zone

        detection_service = get_detection_service()
        person_boxes = detection_service.detect_people(original)

        household_id = _resolve_household_id_for_stream(biz_stream_id)
        output, presence, _events = get_face_service().process_frame(
            original,
            stream_id=biz_stream_id,
            household_id=household_id,
            annotate=True,
            persist_alert=True,
        )
        face_roles = _map_face_roles_to_people(presence, person_boxes)

        zones_qs = Zone.objects.filter(stream_id=biz_stream_id, is_active=True)
        if household_id is not None:
            zones_qs = zones_qs.filter(household_id=household_id)
        zones = [
            {
                "id": z.id,
                "name": z.name,
                "points_json": z.points_json,
                "forbidden_roles": z.forbidden_roles,
                "safe_distance": z.safe_distance,
                "dwell_time": z.dwell_time,
                "is_active": z.is_active,
            }
            for z in zones_qs
        ]

        results = detection_service.process_frame(
            frame=original,
            stream_id=biz_stream_id,
            person_boxes=person_boxes,
            face_roles=face_roles,
            zones=zones if zones else None,
            snapshot_frame=output,
        )
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
            output = get_face_service().draw_face_boxes(output, presence)
        ai_ok = True
    except Exception as exc:
        logger.warning(
            "视频流 %s 的 AI 处理链执行失败: %s",
            stream_id,
            exc,
            exc_info=True,
        )

    ai_status = (
        f"faces:{face_count}  persons:{len(person_boxes)}"
        if ai_ok
        else "AI err"
    )
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
    ok, buffer = cv2.imencode(".jpg", frame)
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
        self.last_error = None
        self.last_frame_at = None
        self.running = False
        self._lock = threading.Lock()
        self._thread = None

    def start(self):
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def _read_loop(self):
        frame_index = 0
        while self.running:
            capture = cv2.VideoCapture(self.stream_url)
            if not capture.isOpened():
                self.last_error = "RTSP stream not available"
                time.sleep(1)
                continue

            self.last_error = None
            try:
                while self.running:
                    ok, frame = capture.read()
                    if not ok:
                        self.last_error = "failed to read frame"
                        time.sleep(0.2)
                        break

                    frame_index += 1
                    if frame_index % self.frame_skip != 0:
                        continue

                    processed_frame = process_frame(frame, self.stream_id)
                    with self._lock:
                        self.latest_frame = processed_frame
                        self.last_frame_at = time.time()
            finally:
                capture.release()

    def get_latest_frame(self):
        with self._lock:
            if self.latest_frame is None:
                return None
            return self.latest_frame.copy()

    def to_status(self):
        return {
            "stream_url": self.stream_url,
            "status": "running" if self.running else "stopped",
            "has_frame": self.latest_frame is not None,
            "last_frame_at": self.last_frame_at,
            "last_error": self.last_error,
        }


def get_worker(stream_id):
    with workers_lock:
        worker = workers.get(stream_id)
        if worker is None:
            worker = CameraWorker(stream_id)
            workers[stream_id] = worker
        worker.start()
        return worker


def get_workers_status():
    return {
        stream_id: worker.to_status()
        for stream_id, worker in workers.items()
    }


def gen_frames(stream_id):
    worker = get_worker(stream_id)
    empty_frame = placeholder_frame("waiting for RTSP frame")
    empty_jpeg = encode_frame(empty_frame)

    while True:
        frame = worker.get_latest_frame()
        jpeg_bytes = encode_frame(frame) if frame is not None else empty_jpeg
        if jpeg_bytes:
            yield multipart_frame(jpeg_bytes)
        time.sleep(0.05)
