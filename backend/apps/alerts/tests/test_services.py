from unittest.mock import Mock, patch

import numpy as np
from django.test import SimpleTestCase

from apps.alerts.services import create_alert


class CreateAlertResilienceTests(SimpleTestCase):
    @patch("apps.video_stream.clips.enqueue_event_clip")
    @patch("apps.events.services.record_event_for_alert")
    @patch("apps.alerts.services.Alert.objects.create")
    @patch(
        "apps.video_stream.snapshots.save_event_snapshot",
        side_effect=OSError("snapshot disk unavailable"),
    )
    def test_snapshot_failure_does_not_block_alert_creation(
        self, _save_snapshot, create_mock, record_event, enqueue_clip
    ):
        alert = Mock(id=17)
        create_mock.return_value = alert
        record_event.return_value = Mock(id=23)

        result = create_alert(
            type="FACE_UNKNOWN",
            level="HIGH",
            stream_id="living_room",
            description="detected stranger",
            household_id=2,
            frame=np.zeros((4, 4, 3), dtype=np.uint8),
        )

        self.assertIs(result, alert)
        self.assertEqual(create_mock.call_args.kwargs["snapshot_path"], "")
        enqueue_clip.assert_called_once_with(17, 23, "living_room", "FACE_UNKNOWN")
