import os
import re
import threading
import time

import cv2
import numpy as np


RTSP_BASE_URL = os.getenv("RTSP_BASE_URL", "rtsp://127.0.0.1:8554/stream")
RTMP_PUBLIC_BASE_URL = os.getenv(
    "RTMP_PUBLIC_BASE_URL", "rtmp://152.136.29.158:9090/stream"
)
FRAME_SKIP = int(os.getenv("VIDEO_FRAME_SKIP", "5"))
STREAM_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")

workers = {}
workers_lock = threading.Lock()


def build_rtsp_url(stream_id):
    return f"{RTSP_BASE_URL.rstrip('/')}/{stream_id}"


def build_public_rtmp_url(stream_id):
    return f"{RTMP_PUBLIC_BASE_URL.rstrip('/')}/{stream_id}"


def process_frame(frame, stream_id):
    """处理单帧：AI 检测 + 标注绘制。

    调用检测模块（李东礼）进行危险区域闯入、积水、着火、摔倒检测，
    并将结果绘制到帧上用于 MJPEG 输出。
    """
    # AI HOOK — 对接检测模块
    try:
        from apps.detection.services import get_detection_service
        from apps.zones.models import Zone

        service = get_detection_service()
        # 获取当前流的活跃危险区域
        zones_qs = Zone.objects.filter(stream_id=stream_id, is_active=True)
        zones = [
            {
                "id": z.id,
                "name": z.name,
                "points_json": z.points_json,
                "forbidden_roles": z.forbidden_roles,
                "is_active": z.is_active,
            }
            for z in zones_qs
        ]

        # TODO: 从人脸模块获取 face_roles 和 person_boxes 后传入
        results = service.process_frame(
            frame=frame,
            stream_id=stream_id,
            zones=zones if zones else None,
        )
        # 绘制检测标注
        frame = service.draw_overlays(frame, results, zones=zones if zones else None)
    except Exception as e:
        # 检测失败不影响视频流正常输出
        import logging

        logging.getLogger(__name__).warning(
            "Detection pipeline error for %s: %s", stream_id, e
        )

    # 叠加流标识
    cv2.putText(
        frame,
        f"stream {stream_id}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        2,
        cv2.LINE_AA,
    )
    return frame


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
