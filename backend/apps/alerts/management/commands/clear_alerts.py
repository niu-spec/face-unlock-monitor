"""清空告警与关联事件记录（测试/联调重置用）。"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.alerts.models import Alert
from apps.events.models import Event


class Command(BaseCommand):
    help = "清空告警记录，可选同时清空事件记录"

    def add_arguments(self, parser):
        parser.add_argument(
            "--household-id",
            type=int,
            help="仅清空指定家庭；省略则清空全部家庭",
        )
        parser.add_argument(
            "--include-events",
            action="store_true",
            help="同时清空 events 表",
        )
        parser.add_argument(
            "--yes",
            action="store_true",
            help="跳过确认提示",
        )

    def handle(self, *args, **options):
        household_id = options.get("household_id")
        include_events = options["include_events"]
        skip_confirm = options["yes"]

        alert_qs = Alert.objects.all()
        event_qs = Event.objects.all()
        if household_id is not None:
            alert_qs = alert_qs.filter(household_id=household_id)
            event_qs = event_qs.filter(household_id=household_id)

        alert_count = alert_qs.count()
        event_count = event_qs.count() if include_events else 0

        scope = f"household_id={household_id}" if household_id else "全部家庭"
        self.stdout.write(
            f"将清空 {scope}：告警 {alert_count} 条"
            + (f"，事件 {event_count} 条" if include_events else "")
        )

        if alert_count == 0 and (not include_events or event_count == 0):
            self.stdout.write(self.style.WARNING("没有需要清空的记录"))
            return

        if not skip_confirm:
            answer = input("确认删除？输入 yes 继续: ").strip().lower()
            if answer != "yes":
                self.stdout.write(self.style.WARNING("已取消"))
                return

        with transaction.atomic():
            deleted_alerts, _ = alert_qs.delete()
            deleted_events = 0
            if include_events:
                deleted_events, _ = event_qs.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"已删除告警 {deleted_alerts} 条"
                + (f"，事件 {deleted_events} 条" if include_events else "")
            )
        )
