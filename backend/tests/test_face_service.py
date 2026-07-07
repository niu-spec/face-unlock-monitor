import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from services.face_service import FaceService


class FaceServiceTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.registry = Path(self.temp_dir.name) / "registered_faces.json"
        self.frame = np.zeros((100, 100, 3), dtype=np.uint8)
        self.service = FaceService(
            registry_path=self.registry,
            resize_scale=1.0,
            tolerance=0.45,
            alert_cooldown=30,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("services.face_service.face_recognition.face_encodings")
    @patch("services.face_service.face_recognition.face_locations")
    def test_register_member_persists_128_dimensions(self, locations, encodings):
        locations.return_value = [(10, 40, 40, 10)]
        encodings.return_value = [np.arange(128, dtype=float) / 128]

        member = self.service.register_member("001", "Alice", "parent", self.frame)

        self.assertEqual(member["member_id"], "001")
        saved = json.loads(self.registry.read_text(encoding="utf-8"))
        self.assertEqual(saved["001"]["role"], "parent")
        self.assertEqual(len(saved["001"]["encoding"]), 128)

        reloaded = FaceService(registry_path=self.registry)
        self.assertEqual(reloaded.list_members()[0]["name"], "Alice")

    @patch("services.face_service.face_recognition.face_encodings")
    @patch("services.face_service.face_recognition.face_locations")
    def test_known_face_is_counted_as_family(self, locations, encodings):
        locations.return_value = [(10, 40, 40, 10)]
        encodings.return_value = [np.zeros(128)]
        self.service._members["001"] = {
            "name": "Alice",
            "role": "parent",
            "encoding": np.zeros(128).tolist(),
        }

        _, presence, events = self.service.process_frame(self.frame, "cam-1")

        self.assertEqual(presence["total"], 1)
        self.assertEqual(presence["family"], 1)
        self.assertEqual(presence["stranger"], 0)
        self.assertEqual(presence["members"][0]["member_id"], "001")
        self.assertEqual(presence["faces"][0]["track_id"], 0)
        self.assertEqual(events, [])

    @patch("services.face_service.face_recognition.face_encodings")
    @patch("services.face_service.face_recognition.face_locations")
    def test_unknown_face_creates_one_cooled_down_alert(self, locations, encodings):
        locations.return_value = [(10, 40, 40, 10)]
        encodings.return_value = [np.ones(128)]
        self.service._members["001"] = {
            "name": "Alice",
            "role": "parent",
            "encoding": np.zeros(128).tolist(),
        }

        _, presence, first_events = self.service.process_frame(self.frame, "cam-1")
        _, _, second_events = self.service.process_frame(self.frame, "cam-1")

        self.assertEqual(presence["stranger"], 1)
        self.assertEqual(first_events[0]["alert_type"], "FACE_UNKNOWN")
        self.assertEqual(second_events, [])
        self.assertEqual(self.service.get_recent_alerts()[0]["status"], "pending")

    @patch("services.face_service.face_recognition.face_locations", return_value=[])
    @patch("services.face_service.face_recognition.face_encodings", return_value=[])
    def test_empty_frame_result_resets_presence(self, _encodings, _locations):
        _, presence, events = self.service.process_frame(self.frame, "cam-1")
        self.assertEqual(presence["total"], 0)
        self.assertEqual(events, [])
        self.assertEqual(self.service.get_presence()["total"], 0)


if __name__ == "__main__":
    unittest.main()
