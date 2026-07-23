import threading
import time
from unittest.mock import Mock, patch

import numpy as np
from django.test import SimpleTestCase

from apps.video_stream.services import (
    CameraWorker,
    _alert_overlay_snapshot,
    _face_overlay_snapshot,
    _person_overlay_snapshot,
    _resolve_alert_overlay_boxes,
    process_frame,
)


class CameraWorkerTests(SimpleTestCase):
    def test_ai_worker_drops_backlog_and_processes_latest_frame(self):
        worker = CameraWorker("1", frame_skip=1)
        worker.running = True
        first_started = threading.Event()
        release_first = threading.Event()
        processed_values = []

        processed_metadata = []

        def fake_process(
            frame,
            stream_id,
            *,
            frame_captured_at=None,
            frame_sequence=None,
        ):
            value = int(frame[0, 0, 0])
            processed_values.append(value)
            processed_metadata.append((frame_captured_at, frame_sequence))
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
                    worker._raw_frame_captured_at = 101.0
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
                        worker._raw_frame_captured_at = 100.0 + value
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
                self.assertEqual(processed_metadata[:2], [(101.0, 1), (110.0, 10)])
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

    def test_capture_loop_detaches_frame_buffer(self):
        worker = CameraWorker("1", frame_skip=1)
        source = np.full((4, 4, 3), 7, dtype=np.uint8)

        with worker._condition:
            worker._raw_frame = source.copy()
            worker._raw_frame_captured_at = 12.0
            worker._capture_sequence = 1

        source.fill(0)

        with worker._condition:
            copied = worker._raw_frame.copy()
            captured_at = worker._raw_frame_captured_at
            sequence = worker._capture_sequence

        self.assertEqual(int(copied[0, 0, 0]), 7)
        self.assertEqual(captured_at, 12.0)
        self.assertEqual(sequence, 1)


class OverlayPublicationTests(SimpleTestCase):
    def test_person_snapshot_carries_matched_face_identity(self):
        presence = {
            "faces": [
                {
                    "box": {"left": 20, "top": 10, "right": 40, "bottom": 30},
                    "known": True,
                    "name": "Alice",
                    "role": "adult",
                    "trusted": False,
                }
            ]
        }

        result = _person_overlay_snapshot(
            presence,
            [{"x": 0, "y": 0, "w": 100, "h": 200, "track_id": 3}],
        )

        self.assertEqual(result[0]["name"], "Alice")
        self.assertTrue(result[0]["known"])
        self.assertFalse(result[0]["trusted"])

    def test_face_snapshot_uses_xywh_coordinates(self):
        presence = {
            "faces": [
                {
                    "track_id": 2,
                    "box": {"left": 20, "top": 10, "right": 60, "bottom": 50},
                    "known": False,
                    "name": "Stranger",
                    "role": "stranger",
                    "trusted": True,
                }
            ]
        }

        result = _face_overlay_snapshot(presence)

        self.assertEqual(result[0]["x"], 20)
        self.assertEqual(result[0]["y"], 10)
        self.assertEqual(result[0]["w"], 40)
        self.assertEqual(result[0]["h"], 40)
        self.assertEqual(result[0]["track_id"], 2)

    def test_alert_snapshot_extracts_fire_and_fall_boxes(self):
        results = [
            {
                "alert_type": "FIRE",
                "bbox": (10, 20, 80, 60),
                "message": "fire",
                "severity": "high",
            },
            {
                "alert_type": "TAILGATE",
                "bbox": (1, 2, 3, 4),
            },
            {
                "alert_type": "FALL",
                "bbox": (30, 40, 50, 20),
                "severity": "high",
            },
        ]

        result = _alert_overlay_snapshot(results)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["alert_type"], "FIRE")
        self.assertEqual(result[0]["w"], 80)
        self.assertEqual(result[1]["alert_type"], "FALL")
        self.assertEqual(result[1]["h"], 20)

    def test_alert_snapshot_extracts_zone_violation_boxes(self):
        results = [
            {
                "alert_type": "INTRUSION",
                "bbox": (5, 6, 40, 30),
                "severity": "high",
            },
            {
                "alert_type": "PROXIMITY",
                "bbox": (1, 2, 3, 4),
            },
        ]

        result = _alert_overlay_snapshot(results)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["alert_type"], "INTRUSION")
        self.assertEqual(result[0]["w"], 40)

    def test_alert_overlay_keeps_recent_boxes_visible(self):
        previous = {
            "alert_boxes": [{"x": 1, "y": 2, "w": 3, "h": 4, "alert_type": "FIRE"}],
            "alert_boxes_updated_at": 100.0,
        }

        boxes, updated_at = _resolve_alert_overlay_boxes(previous, [], now=101.5)

        self.assertEqual(len(boxes), 1)
        self.assertEqual(updated_at, 100.0)

    def test_alert_overlay_expires_stale_boxes(self):
        previous = {
            "alert_boxes": [{"x": 1, "y": 2, "w": 3, "h": 4, "alert_type": "FALL"}],
            "alert_boxes_updated_at": 100.0,
        }

        boxes, updated_at = _resolve_alert_overlay_boxes(previous, [], now=104.0)

        self.assertEqual(boxes, [])
        self.assertIsNone(updated_at)

    @patch("apps.video_stream.services._get_active_zones", return_value=[])
    @patch("apps.video_stream.services._resolve_household_id_for_stream", return_value=1)
    @patch("apps.face.liveness.get_liveness_service")
    @patch("apps.detection.services.get_detection_service")
    @patch("apps.face.services.get_face_service")
    def test_face_presence_is_published_before_person_detection(
        self,
        mock_get_face_service,
        mock_get_detection_service,
        mock_get_liveness_service,
        _mock_household,
        _mock_zones,
    ):
        calls = []
        frame = np.zeros((4, 6, 3), dtype=np.uint8)
        presence = {
            "stream_id": "living_room",
            "faces": [],
            "frame_size": {"width": 6, "height": 4},
        }

        face_service = Mock()
        face_service.get_presence.return_value = {"persons": []}
        face_service.process_frame.return_value = (frame, presence, [])
        face_service.set_presence.side_effect = lambda _value: calls.append("publish")
        face_service.draw_face_boxes.side_effect = lambda output, _presence: output
        mock_get_face_service.return_value = face_service

        detection_service = Mock()
        detection_service.detect_people.side_effect = lambda _frame: (
            calls.append("detect_people")
            or [{"x": 0, "y": 0, "w": 6, "h": 4, "track_id": 7, "confidence": 0.9}]
        )
        detection_service.detect_fire_alerts.return_value = []
        detection_service.detect_fall_alerts.return_value = []
        detection_service.process_frame.return_value = []
        detection_service.draw_overlays.side_effect = (
            lambda output, _results, **_kwargs: output
        )
        mock_get_detection_service.return_value = detection_service

        liveness_service = Mock()
        liveness_service.observe.return_value = ({"status": "passed"}, [])
        mock_get_liveness_service.return_value = liveness_service

        process_frame(
            frame,
            "1",
            frame_captured_at=123.5,
            frame_sequence=42,
        )

        self.assertLess(calls.index("publish"), calls.index("detect_people"))
        first_published = face_service.set_presence.call_args_list[0].args[0]
        self.assertEqual(first_published["frame_captured_at"], 123.5)
        self.assertEqual(first_published["frame_sequence"], 42)
        self.assertEqual(first_published["face_boxes"], [])
        person_published = face_service.set_presence.call_args_list[1].args[0]
        self.assertEqual(
            person_published["persons"],
            [{"x": 0, "y": 0, "w": 6, "h": 4, "track_id": 7, "confidence": 0.9}],
        )
        self.assertEqual(person_published["face_boxes"], [])

    @patch("apps.video_stream.services._get_active_zones", return_value=[])
    @patch("apps.video_stream.services._resolve_household_id_for_stream", return_value=1)
    @patch("apps.face.liveness.get_liveness_service")
    @patch("apps.detection.services.get_detection_service")
    @patch("apps.face.services.get_face_service")
    def test_alert_boxes_are_published_before_liveness(
        self,
        mock_get_face_service,
        mock_get_detection_service,
        mock_get_liveness_service,
        _mock_household,
        _mock_zones,
    ):
        calls = []
        frame = np.zeros((4, 6, 3), dtype=np.uint8)
        presence = {
            "stream_id": "living_room",
            "faces": [
                {
                    "track_id": 0,
                    "box": {"left": 1, "top": 1, "right": 3, "bottom": 3},
                    "known": True,
                    "name": "Bob",
                    "role": "adult",
                    "trusted": True,
                }
            ],
            "frame_size": {"width": 6, "height": 4},
        }

        face_service = Mock()
        face_service.get_presence.return_value = {"persons": [], "alert_boxes": []}
        face_service.process_frame.return_value = (frame, presence, [])
        face_service.set_presence.side_effect = lambda _value: calls.append("publish")
        face_service.draw_face_boxes.side_effect = lambda output, _presence: output
        mock_get_face_service.return_value = face_service

        detection_service = Mock()
        detection_service.detect_fire_alerts.side_effect = lambda *_args, **_kwargs: (
            calls.append("detect_fire")
            or [
                {
                    "alert_type": "FIRE",
                    "bbox": (1, 1, 2, 2),
                    "severity": "high",
                }
            ]
        )
        detection_service.detect_people.side_effect = lambda *_args, **_kwargs: (
            calls.append("detect_people") or []
        )
        detection_service.detect_fall_alerts.side_effect = lambda *_args, **_kwargs: (
            calls.append("detect_fall") or []
        )
        detection_service.process_frame.return_value = []
        detection_service.draw_overlays.side_effect = (
            lambda output, _results, **_kwargs: output
        )
        mock_get_detection_service.return_value = detection_service

        liveness_service = Mock()
        liveness_service.observe.side_effect = lambda *_args, **_kwargs: (
            calls.append("liveness") or ({"status": "passed"}, [])
        )
        mock_get_liveness_service.return_value = liveness_service

        process_frame(frame, "1")

        self.assertLess(calls.index("detect_fire"), calls.index("detect_people"))
        self.assertLess(calls.index("detect_fall"), calls.index("liveness"))
        self.assertIn("publish", calls[calls.index("detect_fire") + 1 : calls.index("liveness")])

        alert_published = next(
            call.args[0]
            for call in face_service.set_presence.call_args_list
            if call.args[0].get("alert_boxes")
        )
        self.assertEqual(
            alert_published["alert_boxes"],
            [{"x": 1, "y": 1, "w": 2, "h": 2, "alert_type": "FIRE", "severity": "high"}],
        )
        detection_service.process_frame.assert_called_once()
        self.assertFalse(
            detection_service.process_frame.call_args.kwargs.get("include_fast", True)
        )

        final_published = face_service.set_presence.call_args_list[-1].args[0]
        self.assertEqual(
            final_published["face_boxes"],
            [{"x": 1, "y": 1, "w": 2, "h": 2, "track_id": 0, "known": True, "name": "Bob", "role": "adult", "trusted": True}],
        )
        self.assertEqual(
            final_published["alert_boxes"],
            [{"x": 1, "y": 1, "w": 2, "h": 2, "alert_type": "FIRE", "severity": "high"}],
        )
        self.assertIn("alert_boxes_updated_at", alert_published)
