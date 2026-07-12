from unittest.mock import MagicMock, patch

import numpy as np
from django.test import SimpleTestCase

from apps.detection.services import (
    DetectionService,
    ZONE_EDITOR_HEIGHT,
    ZONE_EDITOR_WIDTH,
    _distance_point_to_polygon,
    _parse_polygon,
    _parse_polygon_for_frame,
)


class ZoneViolationTests(SimpleTestCase):
    def setUp(self):
        from collections import defaultdict

        with patch.object(DetectionService, "__init__", lambda self: None):
            self.service = DetectionService()
        self.service._cooldown = defaultdict(dict)
        self.service._loiter_since = {}
        self.service._intrusion_counter = defaultdict(lambda: defaultdict(int))
        self.service._fall_counter = defaultdict(int)
        self.service._fall_last_seen = {}
        self.service._person_history = {}
        # 新增的 IoU 追踪器（Mock，测试中 zone 检测不依赖真实追踪）
        self.service._person_tracker = MagicMock()
        self.service._person_tracker._tracks = {}

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
            "kitchen", zones, person_boxes, face_roles, 640, 480
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

        results = []
        # INTRUSION_PERSIST_FRAMES=3：需连续多帧在禁区内才触发闯入告警
        for _ in range(3):
            results = self.service._detect_zone_violations(
                "kitchen", zones, person_boxes, face_roles, 640, 480
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
                "kitchen", zones, person_boxes, face_roles, 640, 480
            )
            self.assertTrue(any(r["alert_type"] == "PROXIMITY" for r in first))

            mock_time.return_value = 1002.0
            second = self.service._detect_zone_violations(
                "kitchen", zones, person_boxes, face_roles, 640, 480
            )

        loiter = [r for r in second if r["alert_type"] == "LOITER"]
        self.assertEqual(len(loiter), 1)

    @patch("apps.detection.services.DetectionService._create_alert")
    def test_adult_role_is_ignored(self, create_alert):
        zones = [self._square_zone()]
        person_boxes = [{"x": 180, "y": 180, "w": 40, "h": 80, "track_id": 3}]
        face_roles = {3: "adult"}

        results = self.service._detect_zone_violations(
            "kitchen", zones, person_boxes, face_roles, 640, 480
        )

        self.assertEqual(results, [])
        create_alert.assert_not_called()

    def test_distance_helper(self):
        polygon = _parse_polygon([[0, 0], [100, 0], [100, 100], [0, 100]])
        inside = _distance_point_to_polygon((50, 50), polygon)
        outside = _distance_point_to_polygon((150, 50), polygon)
        self.assertGreater(inside, 0)
        self.assertLess(outside, 0)

    def test_polygon_scales_to_detection_frame(self):
        points = [[0, 0], [ZONE_EDITOR_WIDTH, 0], [ZONE_EDITOR_WIDTH, ZONE_EDITOR_HEIGHT], [0, ZONE_EDITOR_HEIGHT]]
        polygon = _parse_polygon_for_frame(points, 1280, 720)
        self.assertEqual(int(polygon[1][0][0]), 1280)
        self.assertEqual(int(polygon[2][0][1]), 720)
