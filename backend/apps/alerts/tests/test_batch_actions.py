from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.alerts.models import Alert
from apps.alerts.services import batch_handle_alerts, batch_ignore_alerts
from apps.households.models import Household

User = get_user_model()


class BatchAlertActionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(phone="15333601865", password="123456")
        self.household = Household.objects.create(name="测试家庭", created_by=self.user)
        self.pending_a = Alert.objects.create(
            household=self.household,
            type="INTRUSION",
            level="HIGH",
            stream_id="kitchen",
            description="pending a",
            status="pending",
        )
        self.pending_b = Alert.objects.create(
            household=self.household,
            type="LOITER",
            level="MEDIUM",
            stream_id="kitchen",
            description="pending b",
            status="pending",
        )
        self.handled = Alert.objects.create(
            household=self.household,
            type="FIRE",
            level="HIGH",
            stream_id="kitchen",
            description="already handled",
            status="handled",
        )

    def test_batch_handle_updates_only_pending(self):
        qs = Alert.objects.filter(household=self.household)
        count = batch_handle_alerts(
            [self.pending_a.id, self.pending_b.id, self.handled.id],
            handled_by=self.user,
            queryset=qs,
        )
        self.assertEqual(count, 2)
        self.pending_a.refresh_from_db()
        self.pending_b.refresh_from_db()
        self.handled.refresh_from_db()
        self.assertEqual(self.pending_a.status, "handled")
        self.assertEqual(self.pending_b.status, "handled")
        self.assertEqual(self.handled.status, "handled")

    def test_batch_ignore_updates_only_pending(self):
        qs = Alert.objects.filter(household=self.household)
        count = batch_ignore_alerts([self.pending_a.id], ignored_by=self.user, queryset=qs)
        self.assertEqual(count, 1)
        self.pending_a.refresh_from_db()
        self.pending_b.refresh_from_db()
        self.assertEqual(self.pending_a.status, "ignored")
        self.assertEqual(self.pending_b.status, "pending")
