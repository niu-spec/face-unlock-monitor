"""
通知 AppConfig — 注册信号 + 启动升级检查器。
"""

import os

from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"
    verbose_name = "通知服务"

    def ready(self):
        # 导入信号，连接 post_save handler
        from . import signals  # noqa: F401

        # 启动后台升级检查器
        # runserver 仅在 reload 子进程启动；gunicorn 等生产环境每个 worker 启动一次
        import sys

        is_runserver = "runserver" in sys.argv
        if (is_runserver and os.environ.get("RUN_MAIN") == "true") or not is_runserver:
            from .checker import start_escalation_checker
            start_escalation_checker()
