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
MJPEG_FPS = int(os.getenv("MJPEG_FPS", "12"))
JPEG_QUALITY = int(os.getenv("MJPEG_JPEG_QUALITY", "75"))
RECONNECT_DELAY_SECONDS = float(os.getenv("RTSP_RECONNECT_DELAY", "1"))
RTSP_DRAIN_GRABS = int(os.getenv("RTSP_DRAIN_GRABS", "5"))
STREAM_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")

workers = {}
workers_lock = threading.Lock()


def build_rtsp_url(stream_id):
    return f"{RTSP_BASE_URL.rstrip('/')}/{stream_id}"


def build_public_rtmp_url(stream_id):
    return f"{RTMP_PUBLIC_BASE_URL.rstrip('/')}/{stream_id}"


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
    quality = max(1, min(100, JPEG_QUALITY))
    ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
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
        self.drain_grabs = max(1, RTSP_DRAIN_GRABS)
        self.latest_frame = None
        self.latest_processed_frame = None
        self.last_error = None
        self.last_frame_at = None
        self.last_processed_at = None
        self.last_processed_error = None
        self.frame_seq = 0
        self.latest_processed_seq = 0
        self.running = False
        self._lock = threading.Lock()
        self._start_lock = threading.Lock()
        self._read_thread = None
        self._process_thread = None

    def start(self):
        with self._start_lock:
            if self.running:
                return
            self.running = True
            self._read_thread = threading.Thread(target=self._read_loop, daemon=True)
            self._process_thread = threading.Thread(target=self._process_loop, daemon=True)
            self._read_thread.start()
            self._process_thread.start()

    def _read_latest_frame(self, capture):
        for _ in range(self.drain_grabs):
            if not capture.grab():
                return False, None

        ok, frame = capture.retrieve()
        if not ok or frame is None:
            return False, None
        return True, frame

    def _read_loop(self):
        while self.running:
            capture = None
            try:
                capture = cv2.VideoCapture(self.stream_url)
                try:
                    capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                except Exception:
                    pass

                if not capture.isOpened():
                    with self._lock:
                        self.last_error = "RTSP stream not available"
                    time.sleep(RECONNECT_DELAY_SECONDS)
                    continue

                with self._lock:
                    self.last_error = None
                while self.running:
                    ok, frame = self._read_latest_frame(capture)
                    if not ok:
                        with self._lock:
                            self.last_error = "failed to read latest RTSP frame"
                        break

                    with self._lock:
                        self.latest_frame = frame
                        self.frame_seq += 1
                        self.last_frame_at = time.time()
                        self.last_error = None
            except Exception as exc:
                with self._lock:
                    self.last_error = f"RTSP worker error: {exc}"
            finally:
                if capture is not None:
                    try:
                        capture.release()
                    except Exception:
                        pass

            time.sleep(RECONNECT_DELAY_SECONDS)

    def _process_loop(self):
        processed_seq = 0
        while self.running:
            with self._lock:
                frame_seq = self.frame_seq
                frame = None if self.latest_frame is None else self.latest_frame.copy()

            if frame is None or frame_seq - processed_seq < self.frame_skip:
                time.sleep(0.02)
                continue

            processed_seq = frame_seq
            try:
                processed_frame = process_frame(frame, self.stream_id)
                with self._lock:
                    self.latest_processed_frame = processed_frame
                    self.latest_processed_seq = frame_seq
                    self.last_processed_at = time.time()
                    self.last_processed_error = None
            except Exception as exc:
                with self._lock:
                    self.last_processed_error = f"process_frame failed: {exc}"

            time.sleep(0.001)

    def get_latest_frame(self):
        with self._lock:
            if self.latest_frame is None:
                return None
            if (
                self.latest_processed_frame is not None
                and self.latest_processed_seq == self.frame_seq
            ):
                return self.latest_processed_frame.copy()
            return self.latest_frame.copy()

    def to_status(self):
        with self._lock:
            has_frame = self.latest_frame is not None
            last_frame_at = self.last_frame_at
            last_error = self.last_error
            frame_seq = self.frame_seq
            last_processed_at = self.last_processed_at
            last_processed_error = self.last_processed_error

        return {
            "stream_url": self.stream_url,
            "status": "running" if self.running else "stopped",
            "has_frame": has_frame,
            "last_frame_at": last_frame_at,
            "last_error": last_error,
            "frame_seq": frame_seq,
            "last_processed_at": last_processed_at,
            "last_processed_error": last_processed_error,
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
    with workers_lock:
        return {
            stream_id: worker.to_status()
            for stream_id, worker in workers.items()
        }


def gen_frames(stream_id):
    worker = get_worker(stream_id)
    empty_frame = placeholder_frame("waiting for RTSP frame")
    empty_jpeg = encode_frame(empty_frame)
    frame_interval = 1.0 / max(1, MJPEG_FPS)

    try:
        while True:
            frame = worker.get_latest_frame()
            jpeg_bytes = encode_frame(frame) if frame is not None else empty_jpeg
            if jpeg_bytes:
                yield multipart_frame(jpeg_bytes)
            time.sleep(frame_interval)
    except GeneratorExit:
        return
