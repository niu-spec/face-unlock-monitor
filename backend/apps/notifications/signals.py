"""
信号处理 — Alert 创建时自动触发钉钉通知。
"""

import logging
import threading

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.alerts.models import Alert

logger = logging.getLogger(__name__)


def _start_dingtalk_notification(alert_id: int) -> None:
    from apps.notifications.services import send_alert_notification

    t = threading.Thread(
        target=send_alert_notification,
        args=(alert_id,),
        daemon=True,
        name=f"dingtalk-notify-alert-{alert_id}",
    )
    t.start()
    logger.debug("已启动钉钉通知线程: alert=%s", alert_id)


@receiver(post_save, sender=Alert)
def on_alert_created(sender, instance, created, **kwargs):
    """新告警创建时触发钉钉通知（事务提交后在 daemon thread 中执行）。"""
    if not created:
        return

    transaction.on_commit(lambda: _start_dingtalk_notification(instance.id))
