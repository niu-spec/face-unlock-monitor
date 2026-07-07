import os
import re
import threading
import time

import cv2
import numpy as np
from flask import Blueprint, Response, current_app, jsonify, stream_with_context


video_bp = Blueprint("video", __name__)

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
    base_url = current_app.config.get("RTMP_BASE_URL", RTMP_PUBLIC_BASE_URL)
    return f"{base_url.rstrip('/')}/{stream_id}"


def process_frame(frame, stream_id):
    # AI HOOK:
    # processed_frame, events = ai_pipeline.process_frame(frame, stream_id)
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


@video_bp.get("/video_feed/<stream_id>")
def video_feed(stream_id):
    if not STREAM_ID_PATTERN.match(stream_id):
        return jsonify({"code": 400, "message": "invalid stream_id"}), 400

    return Response(
        stream_with_context(gen_frames(stream_id)),
        mimetype="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-cache"},
    )


@video_bp.get("/api/video/status")
def video_status():
    return jsonify(
        {
            "code": 200,
            "message": "video blueprint running",
            "rtsp_base_url": RTSP_BASE_URL,
            "rtmp_public_base_url": RTMP_PUBLIC_BASE_URL,
            "workers": {
                stream_id: worker.to_status()
                for stream_id, worker in workers.items()
            },
        }
    )


@video_bp.get("/api/video/streams/<stream_id>/source")
def video_source(stream_id):
    if not STREAM_ID_PATTERN.match(stream_id):
        return jsonify({"code": 400, "message": "invalid stream_id"}), 400

    return jsonify(
        {
            "code": 200,
            "stream_id": stream_id,
            "stream_url": build_rtsp_url(stream_id),
            "rtsp_url": build_rtsp_url(stream_id),
            "rtmp_url": build_public_rtmp_url(stream_id),
            "mjpeg_url": f"/video_feed/{stream_id}",
            "frame_skip": FRAME_SKIP,
        }
    )
