from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.alerts.models import Alert
from apps.households.models import Household, HouseholdMembership
from apps.notifications.models import AlertNotification, DingTalkConfig
from apps.notifications.services import process_escalation, resolve_assignee, send_alert_notification

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


class EscalationNotificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(phone="15333601865", password="123456")
        self.supervisor = User.objects.create_user(phone="13800000001", password="123456")
        self.user.supervisor = self.supervisor
        self.user.save(update_fields=["supervisor"])

        self.household = Household.objects.create(name="测试家庭", created_by=self.user)
        for u in (self.user, self.supervisor):
            HouseholdMembership.objects.create(
                household=self.household,
                user=u,
                role="admin",
            )
        DingTalkConfig.objects.create(
            household=self.household,
            webhook_url="https://example.com/webhook",
            secret="secret",
            is_enabled=True,
            escalation_timeout_high=1,
        )
        self.alert = Alert.objects.create(
            household=self.household,
            type="FIRE",
            level="HIGH",
            stream_id="kitchen",
            description="检测到火情",
            status="pending",
            assigned_to=self.user,
            notified_at=timezone.now() - timedelta(seconds=120),
            escalation_level=0,
        )

    @patch("apps.notifications.dingtalk.DingTalkClient.send_markdown")
    def test_escalation_without_dingtalk_user_id(self, send_markdown_mock):
        send_markdown_mock.return_value = {"errcode": 0, "errmsg": "ok"}
        self.assertEqual(self.supervisor.dingtalk_user_id, "")

        triggered = process_escalation(self.alert)

        self.assertTrue(triggered)
        send_markdown_mock.assert_called_once()
        called_kwargs = send_markdown_mock.call_args.kwargs
        self.assertEqual(called_kwargs.get("at_user_ids"), [])

        self.alert.refresh_from_db()
        self.assertEqual(self.alert.escalation_level, 1)
        self.assertEqual(self.alert.assigned_to_id, self.supervisor.id)

    @patch("apps.notifications.dingtalk.DingTalkClient.send_markdown")
    def test_escalation_with_supervisor_dingtalk_user_id(self, send_markdown_mock):
        self.user.supervisor = None
        self.user.supervisor_dingtalk_user_id = "manager001"
        self.user.save(update_fields=["supervisor", "supervisor_dingtalk_user_id"])

        send_markdown_mock.return_value = {"errcode": 0, "errmsg": "ok"}

        triggered = process_escalation(self.alert)

        self.assertTrue(triggered)
        send_markdown_mock.assert_called_once()
        self.assertEqual(send_markdown_mock.call_args.kwargs.get("at_user_ids"), ["manager001"])

        self.alert.refresh_from_db()
        self.assertEqual(self.alert.escalation_level, 1)
        self.assertEqual(self.alert.assigned_to_id, self.user.id)
