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

        # 启动后台升级检查器（仅在主进程中启动，reloader 子进程不启动）
        run_main = os.environ.get("RUN_MAIN")
        if run_main == "true":
            from .checker import start_escalation_checker
            start_escalation_checker()
