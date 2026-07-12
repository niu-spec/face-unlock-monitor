import threading
import time
from unittest.mock import patch

import numpy as np
from django.test import SimpleTestCase

from apps.video_stream.services import CameraWorker


class CameraWorkerTests(SimpleTestCase):
    def test_ai_worker_drops_backlog_and_processes_latest_frame(self):
        worker = CameraWorker("1", frame_skip=1)
        worker.running = True
        first_started = threading.Event()
        release_first = threading.Event()
        processed_values = []

        def fake_process(frame, stream_id):
            value = int(frame[0, 0, 0])
            processed_values.append(value)
            if value == 1:
                first_started.set()
                release_first.wait(timeout=2)
            return frame

        def fake_encode(frame):
            return f"jpeg-{int(frame[0, 0, 0])}".encode()

        thread = threading.Thread(target=worker._process_loop, daemon=True)
        try:
            with patch(
                "apps.video_stream.services.process_frame",
                side_effect=fake_process,
            ), patch(
                "apps.video_stream.services.encode_frame",
                side_effect=fake_encode,
            ):
                thread.start()
                with worker._condition:
                    worker._raw_frame = np.full((2, 2, 3), 1, dtype=np.uint8)
                    worker._capture_sequence = 1
                    worker._condition.notify_all()

                self.assertTrue(first_started.wait(timeout=1))

                # Frames 2..10 arrive while inference of frame 1 is blocked.
                # Only frame 10 should be processed when inference resumes.
                with worker._condition:
                    for value in range(2, 11):
                        worker._raw_frame = np.full(
                            (2, 2, 3), value, dtype=np.uint8
                        )
                        worker._capture_sequence = value
                    worker._condition.notify_all()

                release_first.set()
                deadline = time.time() + 2
                while time.time() < deadline:
                    with worker._condition:
                        if worker._processed_version >= 2:
                            break
                    time.sleep(0.01)

                self.assertGreaterEqual(worker._processed_version, 2)
                self.assertEqual(processed_values[:2], [1, 10])
                self.assertEqual(worker.latest_jpeg, b"jpeg-10")
                self.assertGreaterEqual(worker._dropped_stale_frames, 8)
        finally:
            release_first.set()
            with worker._condition:
                worker.running = False
                worker._condition.notify_all()
            thread.join(timeout=1)

    def test_status_reports_processing_metrics(self):
        worker = CameraWorker("2")
        with worker._condition:
            worker.last_process_duration = 0.125
            worker._capture_sequence = 20
            worker._processed_input_sequence = 15
            worker._dropped_stale_frames = 10
            worker._recent_process_times = [10.0, 10.5, 11.0]

        status = worker.to_status()

        self.assertEqual(status["last_process_duration_ms"], 125.0)
        self.assertEqual(status["process_fps"], 2.0)
        self.assertEqual(status["captured_sequence"], 20)
        self.assertEqual(status["processed_sequence"], 15)
        self.assertEqual(status["dropped_stale_frames"], 10)
