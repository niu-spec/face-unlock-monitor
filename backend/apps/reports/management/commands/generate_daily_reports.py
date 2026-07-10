"""定时为全部家庭生成当日监控日报。"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.households.models import Household
from apps.reports.services import generate_daily_report


class Command(BaseCommand):
    help = "为所有家庭生成当日 AI 监控日报（可配合 cron / 计划任务）"

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            type=str,
            help="指定日期 YYYY-MM-DD，默认今天",
        )
        parser.add_argument(
            "--household-id",
            type=int,
            help="仅生成指定家庭 ID",
        )

    def handle(self, *args, **options):
        if options.get("date"):
            from datetime import date

            report_date = date.fromisoformat(options["date"])
        else:
            report_date = timezone.localdate()

        households = Household.objects.all()
        if options.get("household_id"):
            households = households.filter(id=options["household_id"])

        count = 0
        for household in households:
            report = generate_daily_report(household.id, report_date)
            count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"[{household.name}] {report.report_date} ({report.source})"
                )
            )

        self.stdout.write(self.style.SUCCESS(f"完成，共生成 {count} 份日报"))
