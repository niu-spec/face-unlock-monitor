import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from django.test import override_settings

from apps.video_stream.clips import build_rtsp_url_for_clip, resolve_clip_path


class ClipPathTests(TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._settings = override_settings(CLIP_ROOT=self._tmpdir.name)

    def tearDown(self):
        self._settings.disable()
        self._tmpdir.cleanup()

    def test_resolve_clip_path_blocks_traversal(self):
        with self._settings:
            self.assertIsNone(resolve_clip_path("../secret.mp4"))

    def test_resolve_clip_path_returns_existing_file(self):
        with self._settings:
            clip = Path(self._tmpdir.name) / "demo.mp4"
            clip.write_bytes(b"fake")
            self.assertEqual(resolve_clip_path("demo.mp4"), clip)

    def test_build_rtsp_url_maps_business_stream_id(self):
        with patch(
            "apps.video_stream.services.build_rtsp_url",
            return_value="rtsp://127.0.0.1:8554/stream/2",
        ) as mocked:
            url = build_rtsp_url_for_clip("kitchen")
        self.assertEqual(url, "rtsp://127.0.0.1:8554/stream/2")
        mocked.assert_called_once_with("2")
