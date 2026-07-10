from datetime import date, datetime, time

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.alerts.models import Alert
from apps.households.models import Household
from apps.reports.services import build_template_report, collect_daily_stats, generate_daily_report


class DailyReportServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(phone="13800000099", password="pass")
        self.household = Household.objects.create(
            name="测试家庭", created_by=self.user
        )
        self.report_date = date(2026, 7, 10)
        self.sample_time = timezone.make_aware(
            datetime.combine(self.report_date, time(12, 0))
        )

    def test_template_report_with_no_alerts(self):
        stats = collect_daily_stats(self.household.id, self.report_date)
        summary = build_template_report(stats)
        self.assertIn("2026-07-10", summary)
        self.assertIn("未产生安防告警", summary)

    def test_generate_daily_report_persists(self):
        alert = Alert.objects.create(
            household=self.household,
            type="FACE_UNKNOWN",
            level="HIGH",
            stream_id="kitchen",
            description="检测到陌生人",
        )
        Alert.objects.filter(pk=alert.pk).update(created_at=self.sample_time)

        report = generate_daily_report(self.household.id, self.report_date)
        self.assertEqual(report.stats["total_alerts"], 1)
        self.assertIn("陌生人", report.summary)
        self.assertEqual(report.source, "template")
