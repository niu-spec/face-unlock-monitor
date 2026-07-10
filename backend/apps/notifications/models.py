"""
通知模型。

- DingTalkConfig：每个家庭的钉钉群机器人配置
- AlertNotification：每次通知/升级的审计日志
"""

from django.db import models


class DingTalkConfig(models.Model):
    """每个家庭可配置独立的钉钉群机器人 Webhook"""

    household = models.OneToOneField(
        "households.Household",
        on_delete=models.CASCADE,
        related_name="dingtalk_config",
        verbose_name="所属家庭",
    )
    webhook_url = models.CharField(
        "Webhook地址", max_length=512,
        help_text="钉钉群机器人的 Webhook URL",
    )
    secret = models.CharField(
        "加签密钥", max_length=128, blank=True, default="",
        help_text="钉钉机器人安全设置中的加签密钥（可选）",
    )
    is_enabled = models.BooleanField(
        "启用通知", default=True,
        help_text="关闭后该家庭的告警将不再推送钉钉消息",
    )
    escalation_timeout_high = models.IntegerField(
        "HIGH级别升级超时(秒)", default=60,
    )
    escalation_timeout_medium = models.IntegerField(
        "MEDIUM级别升级超时(秒)", default=300,
    )
    escalation_timeout_low = models.IntegerField(
        "LOW级别升级超时(秒)", default=900,
    )
    default_assignee = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="default_for_configs", verbose_name="默认主R",
        help_text="设置后将覆盖自动选择家庭管理员的逻辑",
    )
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        db_table = "dingtalk_config"
        verbose_name = "钉钉通知配置"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"钉钉配置 [{self.household.name}]"


class AlertNotification(models.Model):
    """每次通知/升级的审计日志"""

    alert = models.ForeignKey(
        "alerts.Alert", on_delete=models.CASCADE,
        related_name="notifications", verbose_name="关联告警",
    )
    escalation_level = models.IntegerField(
        "升级层级", default=0,
        help_text="0=首次通知, 1=+1升级, 2=+2升级...",
    )
    target_user = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="notification_records", verbose_name="目标用户",
    )
    target_dingtalk_id = models.CharField(
        "目标钉钉ID", max_length=128, blank=True, default="",
    )
    success = models.BooleanField("发送成功", default=False)
    error_message = models.TextField("错误信息", blank=True, default="")
    dingtalk_response = models.JSONField(
        "钉钉API响应", default=dict, blank=True,
    )
    created_at = models.DateTimeField("发送时间", auto_now_add=True)

    class Meta:
        db_table = "alert_notification"
        verbose_name = "通知记录"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self):
        status = "成功" if self.success else "失败"
        return f"[Lv.{self.escalation_level}] {self.alert} → {status}"
