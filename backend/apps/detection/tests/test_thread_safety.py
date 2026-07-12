import threading
import time
from unittest.mock import patch

import numpy as np
from django.test import SimpleTestCase

from apps.detection.services import DetectionService, SimplePersonTracker


class DetectionInferenceLockTests(SimpleTestCase):
    def _bare_service(self) -> DetectionService:
        service = DetectionService.__new__(DetectionService)
        service._detector_type = "YOLO"
        service._yolo = object()
        service._person_tracker = SimplePersonTracker()
        service._inference_lock = threading.Lock()
        return service

    def test_detect_people_serializes_concurrent_inference(self):
        service = self._bare_service()
        depth = {"value": 0, "max": 0}
        depth_lock = threading.Lock()

        def slow_yolo(frame):
            with depth_lock:
                depth["value"] += 1
                depth["max"] = max(depth["max"], depth["value"])
            time.sleep(0.05)
            with depth_lock:
                depth["value"] -= 1
            return []

        frame = np.zeros((80, 80, 3), dtype=np.uint8)
        with patch.object(
            DetectionService,
            "_detect_pedestrians_yolo",
            side_effect=slow_yolo,
        ):
            threads = [
                threading.Thread(target=service.detect_people, args=(frame,))
                for _ in range(4)
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=2)
                self.assertFalse(thread.is_alive())

        self.assertEqual(depth["max"], 1)
