import tempfile

import numpy as np
from django.test import SimpleTestCase, override_settings

from apps.video_stream.snapshots import resolve_snapshot_path, save_event_snapshot


class SnapshotTests(SimpleTestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._settings = override_settings(SNAPSHOT_ROOT=self._tmpdir.name)
        self._settings.enable()

    def tearDown(self):
        self._settings.disable()
        self._tmpdir.cleanup()

    def test_save_and_resolve_snapshot(self):
        frame = np.zeros((120, 160, 3), dtype=np.uint8)
        filename = save_event_snapshot(frame, "kitchen", "INTRUSION")
        self.assertTrue(filename.endswith(".jpg"))

        filepath = resolve_snapshot_path(filename)
        self.assertIsNotNone(filepath)
        self.assertTrue(filepath.is_file())

        filepath.unlink(missing_ok=True)

    def test_resolve_rejects_path_traversal(self):
        self.assertIsNone(resolve_snapshot_path("../secret.jpg"))
