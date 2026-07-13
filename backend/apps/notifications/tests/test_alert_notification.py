from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.alerts.models import Alert
from apps.households.models import Household, HouseholdMembership
from apps.notifications.models import AlertNotification, DingTalkConfig
from apps.notifications.services import resolve_assignee, send_alert_notification

User = get_user_model()


class AlertNotificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(phone="15333601865", password="123456")
        self.household = Household.objects.create(name="测试家庭", created_by=self.user)
        HouseholdMembership.objects.create(
            household=self.household,
            user=self.user,
            role="admin",
        )
        self.config = DingTalkConfig.objects.create(
            household=self.household,
            webhook_url="https://example.com/webhook",
            secret="secret",
            is_enabled=True,
        )
        self.alert = Alert.objects.create(
            household=self.household,
            type="FIRE",
            level="HIGH",
            stream_id="kitchen",
            description="检测到火情",
            status="pending",
        )

    def test_resolve_assignee_without_dingtalk_user_id(self):
        assignee = resolve_assignee(self.household.id, self.config)
        self.assertEqual(assignee, self.user)
        self.assertEqual(assignee.dingtalk_user_id, "")

    @patch("apps.notifications.dingtalk.DingTalkClient.send_markdown")
    def test_send_alert_notification_without_dingtalk_user_id(self, send_markdown_mock):
        send_markdown_mock.return_value = {"errcode": 0, "errmsg": "ok"}

        notification = send_alert_notification(self.alert.id)

        self.assertIsNotNone(notification)
        self.assertTrue(notification.success)
        send_markdown_mock.assert_called_once()

        self.alert.refresh_from_db()
        self.assertIsNotNone(self.alert.notified_at)
        self.assertEqual(self.alert.assigned_to_id, self.user.id)

    @patch("apps.notifications.dingtalk.DingTalkClient.send_markdown")
    def test_send_alert_notification_without_assignee(self, send_markdown_mock):
        send_markdown_mock.return_value = {"errcode": 0, "errmsg": "ok"}
        HouseholdMembership.objects.filter(household=self.household).delete()

        notification = send_alert_notification(self.alert.id)

        self.assertIsNotNone(notification)
        self.assertTrue(notification.success)
        send_markdown_mock.assert_called_once()

        self.alert.refresh_from_db()
        self.assertIsNotNone(self.alert.notified_at)
        self.assertIsNone(self.alert.assigned_to_id)
        self.assertEqual(AlertNotification.objects.count(), 1)
