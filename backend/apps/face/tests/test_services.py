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

    @patch("apps.face.services._load_face_recognition")
    def test_process_frame_draws_boxes_when_annotate_true(self, load_library):
        library = Mock()
        library.face_locations.return_value = [(10, 40, 40, 10)]
        library.face_encodings.return_value = [np.zeros(128)]
        library.face_distance.return_value = np.array([0.9])
        load_library.return_value = library

        output, presence, _ = self.service.process_frame(
            self.frame, annotate=True, persist_alert=False
        )

        self.assertEqual(presence["total"], 1)
        self.assertFalse(np.array_equal(output, self.frame))

    @patch("apps.face.services._load_face_recognition")
    def test_process_frame_skips_drawing_when_annotate_false(self, load_library):
        library = Mock()
        library.face_locations.return_value = [(10, 40, 40, 10)]
        library.face_encodings.return_value = [np.zeros(128)]
        library.face_distance.return_value = np.array([0.9])
        load_library.return_value = library

        output, presence, _ = self.service.process_frame(
            self.frame, annotate=False, persist_alert=False
        )

        self.assertEqual(presence["total"], 1)
        self.assertTrue(np.array_equal(output, self.frame))

    def test_draw_face_boxes_from_presence(self):
        presence = {
            "faces": [
                {
                    "known": False,
                    "name": "Stranger",
                    "role": "stranger",
                    "box": {"top": 10, "right": 40, "bottom": 40, "left": 10},
                }
            ]
        }

        annotated = FaceRecognitionService.draw_face_boxes(self.frame, presence)

        self.assertFalse(np.array_equal(annotated, self.frame))

    def test_draw_face_boxes_marks_untrusted_faces(self):
        presence = {
            "faces": [
                {
                    "known": True,
                    "trusted": False,
                    "name": "tester",
                    "role": "adult",
                    "box": {"top": 10, "right": 40, "bottom": 40, "left": 10},
                }
            ]
        }

        annotated = FaceRecognitionService.draw_face_boxes(self.frame, presence)

        self.assertFalse(np.array_equal(annotated, self.frame))

from apps.face.liveness import FACE_SPOOF, LivenessDetectionService


def _liveness_presence(left=20, top=20, right=80, bottom=80):
    return {
        "faces": [
            {
                "known": True,
                "name": "tester",
                "role": "adult",
                "box": {"left": left, "top": top, "right": right, "bottom": bottom},
            }
        ]
    }


def _liveness_pattern_frame(offset=0):
    frame = np.zeros((120, 120, 3), dtype=np.uint8)
    y, x = np.indices((60, 60))
    pattern = ((x * 3 + y * 5 + offset) % 255).astype(np.uint8)
    frame[20:80, 20:80, 0] = pattern
    frame[20:80, 20:80, 1] = np.roll(pattern, shift=offset % 7, axis=1)
    frame[20:80, 20:80, 2] = 255 - pattern
    return frame


class LivenessDetectionServiceTests(TestCase):
    def test_static_face_sequence_emits_spoof_attack_once_per_cooldown(self):
        service = LivenessDetectionService(window_size=4, min_samples=4, alert_cooldown=60)
        frame = _liveness_pattern_frame(0)
        events = []
        result = None

        for _ in range(4):
            result, events = service.observe(
                frame,
                _liveness_presence(),
                stream_id="cam-1",
                persist_alert=False,
            )

        self.assertEqual(result["status"], "attack")
        self.assertEqual(result["attack_type"], FACE_SPOOF)
        self.assertTrue(events)
        self.assertEqual(events[0]["type"], FACE_SPOOF)

        _, repeated = service.observe(
            frame,
            _liveness_presence(),
            stream_id="cam-1",
            persist_alert=False,
        )
        self.assertEqual(repeated, [])

    def test_sequence_with_motion_passes_liveness(self):
        service = LivenessDetectionService(window_size=6, min_samples=4)
        frames = [_liveness_pattern_frame(offset * 17) for offset in range(4)]
        presences = [
            _liveness_presence(20 + offset, 20, 80 + offset, 80)
            for offset in range(4)
        ]

        result = service.analyze_sequence(frames, presences)

        self.assertEqual(result["status"], "passed")
        self.assertTrue(result["passed"])
        self.assertIsNone(result["attack_type"])

    @patch("apps.alerts.services.create_alert")
    def test_attack_alert_persists_current_frame_for_snapshot(self, create_alert):
        service = LivenessDetectionService(window_size=4, min_samples=4, alert_cooldown=60)
        frame = _liveness_pattern_frame(0)

        for _ in range(4):
            service.observe(
                frame,
                _liveness_presence(),
                stream_id="cam-1",
                household_id=2,
                persist_alert=True,
            )

        create_alert.assert_called_once()
        self.assertIs(create_alert.call_args.kwargs["frame"], frame)
        self.assertEqual(create_alert.call_args.kwargs["household_id"], 2)
