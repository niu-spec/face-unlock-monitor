from unittest.mock import patch

from django.test import TestCase

from apps.accounts.models import User
from apps.alerts.models import Alert
from apps.alerts.services import create_alert
from apps.events.models import Event
from apps.households.models import Household


class CreateAlertClipTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(phone="13800000001", password="test")
        self.household = Household.objects.create(name="测试家", created_by=self.user)

    @patch("apps.video_stream.clips.enqueue_event_clip")
    def test_create_alert_enqueues_clip_recording(self, enqueue_mock):
        alert = create_alert(
            type="FACE_UNKNOWN",
            level="HIGH",
            stream_id="kitchen",
            description="厨房检测到陌生人",
            household_id=self.household.id,
        )
        self.assertIsInstance(alert, Alert)
        self.assertEqual(Event.objects.count(), 1)
        event = Event.objects.first()
        enqueue_mock.assert_called_once_with(
            alert.id,
            event.id,
            "kitchen",
            "FACE_UNKNOWN",
        )


class CreateAlertDedupTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(phone="13800000002", password="test")
        self.household = Household.objects.create(name="告警测试家", created_by=self.user)

    @patch("apps.video_stream.clips.enqueue_event_clip")
    def test_same_type_creates_separate_pending_alerts(self, enqueue_mock):
        first = create_alert(
            type="INTRUSION",
            level="HIGH",
            stream_id="kitchen",
            description="第一次闯入",
            household_id=self.household.id,
        )
        second = create_alert(
            type="INTRUSION",
            level="HIGH",
            stream_id="kitchen",
            description="第二次闯入",
            household_id=self.household.id,
        )

        self.assertNotEqual(first.id, second.id)
        self.assertEqual(Alert.objects.filter(type="INTRUSION", status="pending").count(), 2)
        self.assertEqual(enqueue_mock.call_count, 2)

    @patch("apps.video_stream.clips.enqueue_event_clip")
    def test_new_alert_after_handled(self, enqueue_mock):
        first = create_alert(
            type="FIRE",
            level="HIGH",
            stream_id="living_room",
            description="第一次火情",
            household_id=self.household.id,
        )
        first.status = "handled"
        first.save(update_fields=["status"])

        second = create_alert(
            type="FIRE",
            level="HIGH",
            stream_id="living_room",
            description="第二次火情",
            household_id=self.household.id,
        )

        self.assertNotEqual(first.id, second.id)
        self.assertEqual(Alert.objects.filter(type="FIRE").count(), 2)
        self.assertEqual(enqueue_mock.call_count, 2)
