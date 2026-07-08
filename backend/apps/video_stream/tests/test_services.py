from unittest import TestCase
from unittest.mock import patch

from apps.video_stream import services


class VideoStreamWorkerTests(TestCase):
    def setUp(self):
        services.workers.clear()

    def tearDown(self):
        services.workers.clear()

    def test_get_worker_reuses_one_camera_worker_per_stream(self):
        with patch.object(services.CameraWorker, "_read_loop", return_value=None):
            with patch.object(services.threading.Thread, "start", autospec=True) as start:
                first = services.get_worker("1")
                second = services.get_worker("1")

        self.assertIs(first, second)
        self.assertEqual(list(services.workers.keys()), ["1"])
        self.assertEqual(start.call_count, 1)

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
