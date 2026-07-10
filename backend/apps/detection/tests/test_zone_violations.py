from unittest.mock import patch

import numpy as np
from django.test import SimpleTestCase

from apps.detection.services import (
    DetectionService,
    _distance_point_to_polygon,
    _parse_polygon,
)


class ZoneViolationTests(SimpleTestCase):
    def setUp(self):
        from collections import defaultdict

        with patch.object(DetectionService, "__init__", lambda self: None):
            self.service = DetectionService()
        self.service._cooldown = defaultdict(dict)
        self.service._loiter_since = {}

    def _square_zone(self, zone_id=1, safe_distance=50, dwell_time=2):
        return {
            "id": zone_id,
            "name": "厨房禁区",
            "points_json": [[100, 100], [300, 100], [300, 300], [100, 300]],
            "forbidden_roles": ["child"],
            "safe_distance": safe_distance,
            "dwell_time": dwell_time,
            "is_active": True,
        }

    @patch("apps.detection.services.DetectionService._create_alert")
    def test_proximity_outside_but_near_edge(self, create_alert):
        zones = [self._square_zone(safe_distance=80)]
        person_boxes = [{"x": 305, "y": 180, "w": 40, "h": 80, "track_id": 1}]
        face_roles = {1: "child"}

        results = self.service._detect_zone_violations(
            "kitchen", zones, person_boxes, face_roles
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["alert_type"], "PROXIMITY")
        create_alert.assert_called_once()
        self.assertEqual(create_alert.call_args.kwargs["alert_type"], "PROXIMITY")

    @patch("apps.detection.services.DetectionService._create_alert")
    def test_intrusion_takes_precedence_over_proximity(self, create_alert):
        zones = [self._square_zone()]
        person_boxes = [{"x": 180, "y": 180, "w": 40, "h": 80, "track_id": 1}]
        face_roles = {1: "child"}

        results = self.service._detect_zone_violations(
            "kitchen", zones, person_boxes, face_roles
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["alert_type"], "INTRUSION")

    @patch("apps.detection.services.DetectionService._create_alert")
    def test_loiter_after_dwell_threshold(self, create_alert):
        zones = [self._square_zone(dwell_time=1)]
        person_boxes = [{"x": 305, "y": 180, "w": 40, "h": 80, "track_id": 2}]
        face_roles = {2: "child"}

        with patch("apps.detection.services.time.time") as mock_time:
            mock_time.return_value = 1000.0
            first = self.service._detect_zone_violations(
                "kitchen", zones, person_boxes, face_roles
            )
            self.assertTrue(any(r["alert_type"] == "PROXIMITY" for r in first))

            mock_time.return_value = 1002.0
            second = self.service._detect_zone_violations(
                "kitchen", zones, person_boxes, face_roles
            )

        loiter = [r for r in second if r["alert_type"] == "LOITER"]
        self.assertEqual(len(loiter), 1)

    @patch("apps.detection.services.DetectionService._create_alert")
    def test_adult_role_is_ignored(self, create_alert):
        zones = [self._square_zone()]
        person_boxes = [{"x": 180, "y": 180, "w": 40, "h": 80, "track_id": 3}]
        face_roles = {3: "adult"}

        results = self.service._detect_zone_violations(
            "kitchen", zones, person_boxes, face_roles
        )

        self.assertEqual(results, [])
        create_alert.assert_not_called()

    def test_distance_helper(self):
        polygon = _parse_polygon([[0, 0], [100, 0], [100, 100], [0, 100]])
        inside = _distance_point_to_polygon((50, 50), polygon)
        outside = _distance_point_to_polygon((150, 50), polygon)
        self.assertLess(inside, 0)
        self.assertGreater(outside, 0)
