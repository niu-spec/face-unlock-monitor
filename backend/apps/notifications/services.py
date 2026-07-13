"""
通知服务层 — 钉钉消息发送 + 升级逻辑。
"""

import logging
import threading

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.alerts.models import Alert
from apps.notifications.models import AlertNotification, DingTalkConfig

logger = logging.getLogger(__name__)

# 告警级别 → 配置键名 映射
LEVEL_TIMEOUT_MAP = {
    "HIGH": "escalation_timeout_high",
    "MEDIUM": "escalation_timeout_medium",
    "LOW": "escalation_timeout_low",
}


def get_dingtalk_config(household_id: int | None) -> DingTalkConfig | None:
    """获取指定家庭的钉钉通知配置。

    优先级: household 级别 → 全局 settings → None（跳过通知）
    """
    if household_id:
        try:
            config = DingTalkConfig.objects.select_related("default_assignee").get(
                household_id=household_id, is_enabled=True
            )
            if config.webhook_url:
                return config
        except DingTalkConfig.DoesNotExist:
            pass

    # Fallback to global settings
    global_url = getattr(settings, "DINGTALK", {}).get("WEBHOOK_URL", "")
    if global_url:
        # 返回一个未保存的临时配置对象
        dingtalk_cfg = getattr(settings, "DINGTALK", {})
        return DingTalkConfig(
            webhook_url=global_url,
            secret=dingtalk_cfg.get("SECRET", ""),
            escalation_timeout_high=dingtalk_cfg.get("ESCALATION_TIMEOUT_HIGH", 60),
            escalation_timeout_medium=dingtalk_cfg.get("ESCALATION_TIMEOUT_MEDIUM", 300),
            escalation_timeout_low=dingtalk_cfg.get("ESCALATION_TIMEOUT_LOW", 900),
        )

    return None


def resolve_assignee(household_id: int | None, config: DingTalkConfig | None = None):
    """确定主 R（主要责任人）。

    优先级:
    1. DingTalkConfig.default_assignee（显式配置）
    2. 家庭管理员中第一个有 dingtalk_user_id 的（用于 @ 提醒）
    3. 任意家庭管理员（无 dingtalk_user_id 时仍可推送群消息，只是无法 @）

    Returns:
        User 对象或 None。
    """
    if config and config.default_assignee_id:
        return config.default_assignee

    if not household_id:
        return None

    from apps.accounts.models import User

    admin_qs = User.objects.filter(
        memberships__household_id=household_id,
        memberships__role="admin",
    )
    admin_with_dingtalk = admin_qs.exclude(dingtalk_user_id="").first()
    if admin_with_dingtalk:
        return admin_with_dingtalk
    return admin_qs.first()


def build_alert_message(alert: Alert, target_user, is_escalation: bool = False) -> str:
    """构建钉钉 Markdown 告警消息。

    Args:
        alert: 告警实例。
        target_user: 被 @ 的目标用户。
        is_escalation: 是否为升级消息（会在消息中标注"已升级"）。

    Returns:
        Markdown 格式的告警消息文本。
    """
    level_emoji = {"HIGH": "🔴", "MEDIUM": "🟠", "LOW": "🟡"}
    level_color = {"HIGH": "#dd0000", "MEDIUM": "#ff8800", "LOW": "#888888"}
    emoji = level_emoji.get(alert.level, "📢")
    color = level_color.get(alert.level, "#333333")

    escalation_tag = ""
    if is_escalation and alert.escalation_level > 0:
        escalation_tag = f"\n> ⚠️ **已升级至 Lv.{alert.escalation_level}** — 原负责人未在规定时间内响应"

    user_mention = ""
    if target_user and target_user.dingtalk_user_id:
        user_mention = f"\n> 👤 **负责人**: @{target_user.phone}"
    elif target_user:
        user_mention = f"\n> 👤 **负责人**: {target_user.phone}"

    message = f"""# {emoji} 安防告警

> **类型**: {alert.get_type_display()} ({alert.type})
> **等级**: <font color="{color}">{alert.get_level_display()}</font>
> **位置**: {alert.stream_id}
> **时间**: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}
{escalation_tag}
{user_mention}

**详情**: {alert.description}

---
📋 请及时登录系统处理该告警"""

    return message


def send_to_dingtalk(alert: Alert, user, escalation_level: int) -> AlertNotification:
    """发送钉钉消息并创建通知记录。

    Args:
        alert: 告警实例。
        user: 目标用户（用于 @ 和记录）。
        escalation_level: 0=首次通知, 1=+1升级, ...

    Returns:
        AlertNotification 记录。
    """
    is_escalation = escalation_level > 0
    dingtalk_user_id = ""
    dingtalk_mobile = ""

    if user:
        dingtalk_user_id = user.dingtalk_user_id or ""
        dingtalk_mobile = user.dingtalk_mobile or ""

    at_user_ids = [dingtalk_user_id] if dingtalk_user_id else []
    at_mobiles = [dingtalk_mobile] if dingtalk_mobile else []

    config = get_dingtalk_config(alert.household_id)

    if not config:
        return AlertNotification.objects.create(
            alert=alert,
            escalation_level=escalation_level,
            target_user=user,
            target_dingtalk_id=dingtalk_user_id,
            success=False,
            error_message="未配置钉钉 Webhook（家庭级别和全局级别均未配置）",
        )

    from apps.notifications.dingtalk import DingTalkClient

    client = DingTalkClient(config.webhook_url, config.secret or "")
    message = build_alert_message(alert, user, is_escalation=is_escalation)

    title_prefix = getattr(settings, "DINGTALK", {}).get("MESSAGE_TITLE_PREFIX", "安防告警")
    title = f"{title_prefix} - {alert.get_type_display()}"
    if is_escalation:
        title = f"⬆️ [升级Lv.{escalation_level}] {title}"

    response = client.send_markdown(
        title=title,
        text=message,
        at_user_ids=at_user_ids,
        at_mobiles=at_mobiles,
    )

    success = response.get("errcode") == 0
    notification = AlertNotification.objects.create(
        alert=alert,
        escalation_level=escalation_level,
        target_user=user,
        target_dingtalk_id=dingtalk_user_id,
        success=success,
        error_message="" if success else response.get("errmsg", "未知错误"),
        dingtalk_response=response,
    )

    if success:
        logger.info(
            "钉钉通知发送成功: alert=%s type=%s level=%s escalation=%s user=%s",
            alert.id, alert.type, alert.level, escalation_level,
            dingtalk_user_id or "unknown",
        )
    else:
        logger.warning(
            "钉钉通知发送失败: alert=%s errcode=%s errmsg=%s",
            alert.id, response.get("errcode"), response.get("errmsg"),
        )

    return notification


def send_alert_notification(alert_id: int) -> AlertNotification | None:
    """新告警通知入口 — 确定主 R 并发送首次钉钉通知。

    在 daemon thread 中运行，不阻塞告警创建路径。

    Args:
        alert_id: Alert 主键（传 ID 而非 ORM 对象以避免线程安全问题）。

    Returns:
        AlertNotification 记录或 None。
    """
    try:
        alert = Alert.objects.select_related("household").get(id=alert_id)
    except Alert.DoesNotExist:
        logger.error("send_alert_notification: 告警 %s 不存在", alert_id)
        return None

    config = get_dingtalk_config(alert.household_id)
    if not config:
        logger.info("告警 %s 无可用钉钉配置，跳过通知", alert_id)
        return None

    assignee = resolve_assignee(alert.household_id, config)
    if assignee and not assignee.dingtalk_user_id:
        logger.info(
            "告警 %s 负责人 %s 未配置钉钉 UserID，仍向群推送（不 @）",
            alert_id,
            assignee.phone,
        )
    elif not assignee:
        logger.info("告警 %s 无负责人，仍向群推送通知", alert_id)

    notification = send_to_dingtalk(alert, assignee, escalation_level=0)

    update_fields = {
        "escalation_level": 0,
        "notified_at": timezone.now(),
    }
    if assignee:
        update_fields["assigned_to"] = assignee
    Alert.objects.filter(id=alert.id).update(**update_fields)

    return notification


# ── 升级引擎 ─────────────────────────────────────────────────────────


def resolve_next_in_chain(alert: Alert):
    """沿 supervisor 链查找下一个有 dingtalk_user_id 的人。

    安全机制:
    - 检查循环引用（visited set）
    - 不超过最大升级层级（默认 3）
    - 跳过没有 dingtalk_user_id 的用户

    Returns:
        User 对象或 None（链已耗尽）。
    """
    max_level = getattr(settings, "DINGTALK", {}).get("MAX_ESCALATION_LEVEL", 3)
    if alert.escalation_level >= max_level:
        return None

    current = alert.assigned_to
    visited = alert.metadata.get("escalation_chain", [])
    if current:
        visited.append(current.id)

    # 沿 supervisor 链向上找
    while current and current.supervisor_id:
        supervisor = current.supervisor
        if supervisor.id in visited:
            logger.warning("升级链检测到循环引用: alert=%s user=%s", alert.id, supervisor.id)
            break
        visited.append(supervisor.id)
        if supervisor.dingtalk_user_id:
            return supervisor
        current = supervisor

    return None


def process_escalation(alert: Alert) -> bool:
    """检查单个告警是否需要升级，如需要则执行升级。

    Args:
        alert: 待检查的告警。

    Returns:
        True 如果触发了升级，False 否则。
    """
    if alert.status != "pending":
        return False
    if not alert.notified_at:
        return False

    config = get_dingtalk_config(alert.household_id)
    if not config:
        return False

    # 获取该级别的超时时间
    timeout_attr = LEVEL_TIMEOUT_MAP.get(alert.level, "escalation_timeout_medium")
    timeout_seconds = getattr(config, timeout_attr, 300)

    # 计算已过时间（从最近一次通知/升级开始计算）
    last_event = alert.escalation_last_at or alert.notified_at
    elapsed = (timezone.now() - last_event).total_seconds()

    if elapsed < timeout_seconds:
        return False  # 未到超时

    # 需要升级
    next_user = resolve_next_in_chain(alert)
    if not next_user:
        alert.metadata["escalation_exhausted"] = True
        alert.metadata["escalation_exhausted_at"] = timezone.now().isoformat()
        alert.save(update_fields=["metadata"])
        logger.info("告警 %s 升级链已耗尽，停止升级", alert.id)
        return False

    # 执行升级
    new_level = alert.escalation_level + 1
    send_to_dingtalk(alert, next_user, escalation_level=new_level)

    # 更新告警
    chain = alert.metadata.get("escalation_chain", [])
    chain.append(next_user.id)
    alert.assigned_to = next_user
    alert.escalation_level = new_level
    alert.escalation_last_at = timezone.now()
    alert.metadata["escalation_chain"] = chain
    alert.save(update_fields=[
        "assigned_to", "escalation_level", "escalation_last_at", "metadata",
    ])

    logger.info(
        "告警 %s 已升级: Lv.%d → %s (dingtalk_id=%s)",
        alert.id, new_level, next_user.phone, next_user.dingtalk_user_id,
    )
    return True


def process_all_escalations() -> int:
    """查询并处理所有需要升级的告警。

    使用 select_for_update() 防止并发重复升级。

    Returns:
        本次触发的升级次数。
    """
    from django.db import transaction

    with transaction.atomic():
        pending_alerts = (
            Alert.objects
            .select_for_update(skip_locked=True)
            .select_related("assigned_to", "assigned_to__supervisor")
            .filter(
                status="pending",
                notified_at__isnull=False,
                metadata__escalation_exhausted__isnull=True,
            )
        )

        count = 0
        for alert in pending_alerts:
            try:
                if process_escalation(alert):
                    count += 1
            except Exception:
                logger.exception("处理告警升级失败: alert=%s", alert.id)

    return count
