import json
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch

import numpy as np

from apps.face.services import FaceRecognitionService


class FaceRecognitionServiceTests(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.registry = Path(self.temp_dir.name) / "registered_faces.json"
        self.service = FaceRecognitionService(
            registry_path=self.registry, resize_scale=1.0, unknown_alert_cooldown=30
        )
        self.frame = np.zeros((100, 100, 3), dtype=np.uint8)

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("apps.face.services._load_face_recognition")
    def test_registration_persists_128_dimensions(self, load_library):
        library = Mock()
        library.face_locations.return_value = [(10, 40, 40, 10)]
        library.face_encodings.return_value = [np.zeros(128)]
        load_library.return_value = library

        member, encoding = self.service.register_member(
            7, "张三", "adult", self.frame, household_id=2
        )

        self.assertEqual(member["member_id"], "7")
        self.assertEqual(len(encoding), 128)
        stored = json.loads(self.registry.read_text(encoding="utf-8"))
        self.assertEqual(stored["7"]["role"], "adult")
        self.assertEqual(stored["7"]["household_id"], 2)

    @patch("apps.face.services._load_face_recognition")
    def test_known_and_unknown_counts_and_alert_cooldown(self, load_library):
        library = Mock()
        library.face_locations.return_value = [
            (10, 40, 40, 10), (20, 80, 60, 50)
        ]
        library.face_encodings.return_value = [np.zeros(128), np.ones(128)]
        library.face_distance.side_effect = [
            np.array([0.2]), np.array([0.9]), np.array([0.2]), np.array([0.9])
        ]
        load_library.return_value = library
        self.service.register_encoding(7, "张三", "adult", np.zeros(128), 2)

        _, presence, events = self.service.process_frame(
            self.frame, "cam-1", household_id=2, persist_alert=False
        )
        _, _, repeated = self.service.process_frame(
            self.frame, "cam-1", household_id=2, persist_alert=False
        )

        self.assertEqual(presence["total"], 2)
        self.assertEqual(presence["family"], 1)
        self.assertEqual(presence["stranger"], 1)
        self.assertEqual(events[0]["type"], "FACE_UNKNOWN")
        self.assertEqual(repeated, [])

    @patch("apps.face.services._load_face_recognition")
    def test_no_face_returns_zero_presence(self, load_library):
        library = Mock()
        library.face_locations.return_value = []
        library.face_encodings.return_value = []
        load_library.return_value = library

        _, presence, events = self.service.process_frame(
            self.frame, persist_alert=False
        )

        self.assertEqual(presence["total"], 0)
        self.assertEqual(events, [])
