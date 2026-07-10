"""
后台升级检查器 — 每 30 秒轮询一次，检查是否有告警需要升级。
"""

import logging
import threading
import time

from django.conf import settings

logger = logging.getLogger(__name__)

_checker_started = False
_checker_lock = threading.Lock()


def start_escalation_checker():
    """启动后台升级检查线程（仅启动一次）。"""
    global _checker_started
    with _checker_lock:
        if _checker_started:
            return
        _checker_started = True

    interval = getattr(settings, "DINGTALK", {}).get("CHECKER_INTERVAL", 30)
    t = threading.Thread(
        target=_checker_loop,
        args=(interval,),
        daemon=True,
        name="dingtalk-escalation-checker",
    )
    t.start()
    logger.info("钉钉升级检查器已启动，间隔=%ss", interval)


def _checker_loop(interval: int):
    """升级检查主循环。"""
    # 启动后等待第一个间隔再执行，给首次通知留出时间
    time.sleep(interval)

    while True:
        try:
            from apps.notifications.services import process_all_escalations

            count = process_all_escalations()
            if count:
                logger.info("升级检查: 本次触发 %s 次升级", count)
        except Exception:
            logger.exception("升级检查器异常")
        time.sleep(interval)
