"""
管理命令 — 检查并处理告警升级（生产环境备选方案）。

用法:
    python manage.py check_escalations

适用场景:
    - 生产环境使用 cron / systemd timer 周期性调用
    - 避免 gunicorn 多 worker 下后台线程重复执行的问题
"""

import logging

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "检查待处理的告警并执行逐级升级"

    def handle(self, **options):
        from apps.notifications.services import process_all_escalations

        try:
            count = process_all_escalations()
            if count:
                self.stdout.write(
                    self.style.WARNING(f"升级检查完成: 触发了 {count} 次升级")
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS("升级检查完成: 无需升级")
                )
        except Exception:
            logger.exception("升级检查命令执行失败")
            self.stderr.write(self.style.ERROR("升级检查失败，详见日志"))
