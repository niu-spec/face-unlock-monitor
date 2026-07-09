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
MJPEG_FPS = int(os.getenv("MJPEG_FPS", "10"))
JPEG_QUALITY = int(os.getenv("MJPEG_JPEG_QUALITY", "75"))
RECONNECT_DELAY_SECONDS = float(os.getenv("RTSP_RECONNECT_DELAY", "1"))
RTSP_DRAIN_GRABS = int(os.getenv("RTSP_DRAIN_GRABS", "5"))
STALE_FRAME_SECONDS = float(os.getenv("STALE_FRAME_SECONDS", "3"))
STREAM_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")

workers = {}
workers_lock = threading.Lock()


def _close_old_db_connections():
    try:
        from django.db import close_old_connections

        close_old_connections()
    except Exception:
        pass


def _detect_person_boxes(frame):
    from apps.detection.services import get_detection_service

    service = get_detection_service()
    return service._detect_pedestrians(frame)


def _draw_person_boxes(frame, person_boxes):
    for box in person_boxes:
        x = int(box.get("x", 0))
        y = int(box.get("y", 0))
        w = int(box.get("w", 0))
        h = int(box.get("h", 0))
        if w <= 0 or h <= 0:
            continue
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 255), 2)
        cv2.putText(
            frame,
            "person",
            (x, max(20, y - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 255),
            2,
            cv2.LINE_AA,
        )


def _draw_diagnostic(frame, text, color):
    cv2.rectangle(frame, (10, 10), (430, 58), (0, 0, 0), -1)
    cv2.putText(
        frame,
        text[:42],
        (20, 44),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        color,
        2,
        cv2.LINE_AA,
    )


def build_rtsp_url(stream_id):
    return f"{RTSP_BASE_URL.rstrip('/')}/{stream_id}"


def build_public_rtmp_url(stream_id):
    return f"{RTMP_PUBLIC_BASE_URL.rstrip('/')}/{stream_id}"


def process_frame(frame, stream_id):
    _close_old_db_connections()
    try:
        from apps.face.services import get_face_service

        face_frame, presence, _events = get_face_service().process_frame(
            frame,
            stream_id=stream_id,
            annotate=True,
            persist_alert=True,
        )
        output = face_frame
        person_boxes = []
        detection_error = None
        try:
            from apps.detection.services import get_detection_service

            person_boxes = _detect_person_boxes(face_frame)
            detection_service = get_detection_service()
            detection_results = detection_service.process_frame(
                face_frame,
                stream_id=stream_id,
                person_boxes=person_boxes,
                face_roles={
                    face["track_id"]: face["role"]
                    for face in presence.get("faces", [])
                    if "track_id" in face and "role" in face
                },
            )
            output = detection_service.draw_overlays(
                face_frame,
                detection_results,
                person_boxes=person_boxes,
            )
            _draw_person_boxes(output, person_boxes)
        except Exception as exc:
            detection_error = type(exc).__name__

        diagnostic = f"AI ok faces:{presence.get('total', 0)} persons:{len(person_boxes)}"
        if detection_error:
            diagnostic = f"{diagnostic} det:{detection_error}"
        _draw_diagnostic(
            output,
            diagnostic,
            (0, 255, 0),
        )
        return output
    except Exception as exc:
        output = frame.copy()
        _draw_diagnostic(output, f"AI err {type(exc).__name__}", (0, 0, 255))
        return output
    finally:
        _close_old_db_connections()


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
        self.latest_jpeg = None
        self.latest_jpeg_seq = 0
        self.latest_jpeg_at = None
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
        self._encode_thread = None

    def start(self):
        with self._start_lock:
            if self.running:
                return
            self.running = True
            self._read_thread = threading.Thread(target=self._read_loop, daemon=True)
            self._process_thread = threading.Thread(target=self._process_loop, daemon=True)
            self._encode_thread = threading.Thread(target=self._encode_loop, daemon=True)
            self._read_thread.start()
            self._process_thread.start()
            self._encode_thread.start()

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

    def _get_output_frame_snapshot(self):
        with self._lock:
            if self.latest_frame is None:
                return None, None
            if (
                self.last_frame_at is None
                or time.time() - self.last_frame_at > STALE_FRAME_SECONDS
            ):
                return None, None
            if (
                self.latest_processed_frame is not None
                and self.latest_processed_seq == self.frame_seq
            ):
                return self.latest_processed_frame.copy(), self.frame_seq
            return self.latest_frame.copy(), self.frame_seq

    def _encode_loop(self):
        encoded_seq = 0
        frame_interval = 1.0 / max(1, MJPEG_FPS)

        while self.running:
            frame, frame_seq = self._get_output_frame_snapshot()
            if frame is None:
                with self._lock:
                    self.latest_jpeg = None
                    self.latest_jpeg_seq = 0
                    self.latest_jpeg_at = None
                time.sleep(frame_interval)
                continue

            if frame_seq == encoded_seq:
                time.sleep(frame_interval)
                continue

            jpeg_bytes = encode_frame(frame)
            if jpeg_bytes:
                with self._lock:
                    self.latest_jpeg = jpeg_bytes
                    self.latest_jpeg_seq = frame_seq
                    self.latest_jpeg_at = time.time()
                encoded_seq = frame_seq

            time.sleep(frame_interval)

    def get_latest_frame(self):
        frame, _ = self._get_output_frame_snapshot()
        return frame

    def get_latest_jpeg(self):
        with self._lock:
            if (
                self.latest_jpeg is None
                or self.latest_jpeg_at is None
                or self.last_frame_at is None
                or time.time() - self.last_frame_at > STALE_FRAME_SECONDS
            ):
                return None
            return self.latest_jpeg

    def to_status(self):
        with self._lock:
            is_fresh = (
                self.latest_frame is not None
                and self.last_frame_at is not None
                and time.time() - self.last_frame_at <= STALE_FRAME_SECONDS
            )
            has_frame = is_fresh
            last_frame_at = self.last_frame_at
            last_error = self.last_error
            frame_seq = self.frame_seq
            latest_jpeg_at = self.latest_jpeg_at
            latest_jpeg_seq = self.latest_jpeg_seq
            last_processed_at = self.last_processed_at
            last_processed_error = self.last_processed_error

        return {
            "stream_url": self.stream_url,
            "status": "running" if self.running else "stopped",
            "has_frame": has_frame,
            "stale_frame_seconds": STALE_FRAME_SECONDS,
            "last_frame_at": last_frame_at,
            "last_error": last_error,
            "frame_seq": frame_seq,
            "latest_jpeg_at": latest_jpeg_at,
            "latest_jpeg_seq": latest_jpeg_seq,
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
            jpeg_bytes = worker.get_latest_jpeg() or empty_jpeg
            if jpeg_bytes:
                yield multipart_frame(jpeg_bytes)
            time.sleep(frame_interval)
    except GeneratorExit:
        return
