from unittest import TestCase
from unittest.mock import patch

import numpy as np

from apps.video_stream import services


class VideoStreamWorkerTests(TestCase):
    def setUp(self):
        services.workers.clear()

    def tearDown(self):
        services.workers.clear()

    def test_get_worker_reuses_one_camera_worker_per_stream(self):
        with patch.object(services.CameraWorker, "_read_loop", return_value=None):
            with patch.object(services.CameraWorker, "_process_loop", return_value=None):
                with patch.object(services.threading.Thread, "start", autospec=True) as start:
                    first = services.get_worker("1")
                    second = services.get_worker("1")

        self.assertIs(first, second)
        self.assertEqual(list(services.workers.keys()), ["1"])
        self.assertEqual(start.call_count, 2)

    def test_read_latest_frame_drops_grabbed_frames_before_retrieve(self):
        class Capture:
            def __init__(self):
                self.grabs = 0
                self.retrieves = 0

            def grab(self):
                self.grabs += 1
                return True

            def retrieve(self):
                self.retrieves += 1
                return True, np.ones((2, 2, 3), dtype=np.uint8)

        worker = services.CameraWorker("1")
        capture = Capture()

        ok, frame = worker._read_latest_frame(capture)

        self.assertTrue(ok)
        self.assertIsNotNone(frame)
        self.assertEqual(capture.grabs, worker.drain_grabs)
        self.assertEqual(capture.retrieves, 1)

    def test_get_latest_frame_prefers_raw_when_processed_frame_is_stale(self):
        worker = services.CameraWorker("1")
        raw = np.ones((2, 2, 3), dtype=np.uint8)
        stale_processed = np.zeros((2, 2, 3), dtype=np.uint8)

        with worker._lock:
            worker.latest_frame = raw
            worker.last_frame_at = services.time.time()
            worker.frame_seq = 10
            worker.latest_processed_frame = stale_processed
            worker.latest_processed_seq = 9

        frame = worker.get_latest_frame()

        self.assertTrue(np.array_equal(frame, raw))

    def test_get_latest_frame_returns_none_after_stale_timeout(self):
        worker = services.CameraWorker("1")
        with worker._lock:
            worker.latest_frame = np.ones((2, 2, 3), dtype=np.uint8)
            worker.last_frame_at = services.time.time() - services.STALE_FRAME_SECONDS - 0.1

        self.assertIsNone(worker.get_latest_frame())

    def test_status_marks_stale_frame_as_no_frame(self):
        worker = services.CameraWorker("1")
        with worker._lock:
            worker.latest_frame = np.ones((2, 2, 3), dtype=np.uint8)
            worker.last_frame_at = services.time.time() - services.STALE_FRAME_SECONDS - 0.1

        status = worker.to_status()

        self.assertFalse(status["has_frame"])
        self.assertEqual(status["stale_frame_seconds"], services.STALE_FRAME_SECONDS)

    def test_gen_frames_returns_waiting_placeholder_when_no_frame(self):
        class EmptyWorker:
            def get_latest_frame(self):
                return None

        with patch.object(services, "get_worker", return_value=EmptyWorker()):
            generator = services.gen_frames("1")
            chunk = next(generator)
            generator.close()

        self.assertTrue(chunk.startswith(b"--frame\r\n"))
        self.assertIn(b"Content-Type: image/jpeg", chunk)
