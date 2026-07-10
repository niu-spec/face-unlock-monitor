# Generated migration — initial notifications app models

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("alerts", "0002_add_notification_fields"),
        ("households", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AlertNotification",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "escalation_level",
                    models.IntegerField(
                        default=0,
                        help_text="0=首次通知, 1=+1升级, 2=+2升级...",
                        verbose_name="升级层级",
                    ),
                ),
                (
                    "target_dingtalk_id",
                    models.CharField(
                        blank=True, default="", max_length=128, verbose_name="目标钉钉ID"
                    ),
                ),
                (
                    "success",
                    models.BooleanField(default=False, verbose_name="发送成功"),
                ),
                (
                    "error_message",
                    models.TextField(blank=True, default="", verbose_name="错误信息"),
                ),
                (
                    "dingtalk_response",
                    models.JSONField(
                        blank=True, default=dict, verbose_name="钉钉API响应"
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="发送时间"),
                ),
                (
                    "alert",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="notifications",
                        to="alerts.alert",
                        verbose_name="关联告警",
                    ),
                ),
                (
                    "target_user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.SET_NULL,
                        related_name="notification_records",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="目标用户",
                    ),
                ),
            ],
            options={
                "verbose_name": "通知记录",
                "verbose_name_plural": "通知记录",
                "db_table": "alert_notification",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="DingTalkConfig",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "webhook_url",
                    models.CharField(
                        help_text="钉钉群机器人的 Webhook URL",
                        max_length=512,
                        verbose_name="Webhook地址",
                    ),
                ),
                (
                    "secret",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="钉钉机器人安全设置中的加签密钥（可选）",
                        max_length=128,
                        verbose_name="加签密钥",
                    ),
                ),
                (
                    "is_enabled",
                    models.BooleanField(
                        default=True,
                        help_text="关闭后该家庭的告警将不再推送钉钉消息",
                        verbose_name="启用通知",
                    ),
                ),
                (
                    "escalation_timeout_high",
                    models.IntegerField(
                        default=60, verbose_name="HIGH级别升级超时(秒)"
                    ),
                ),
                (
                    "escalation_timeout_medium",
                    models.IntegerField(
                        default=300, verbose_name="MEDIUM级别升级超时(秒)"
                    ),
                ),
                (
                    "escalation_timeout_low",
                    models.IntegerField(
                        default=900, verbose_name="LOW级别升级超时(秒)"
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="创建时间"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="更新时间"),
                ),
                (
                    "default_assignee",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.SET_NULL,
                        related_name="default_for_configs",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="默认主R",
                        help_text="设置后将覆盖自动选择家庭管理员的逻辑",
                    ),
                ),
                (
                    "household",
                    models.OneToOneField(
                        on_delete=models.CASCADE,
                        related_name="dingtalk_config",
                        to="households.household",
                        verbose_name="所属家庭",
                    ),
                ),
            ],
            options={
                "verbose_name": "钉钉通知配置",
                "verbose_name_plural": "钉钉通知配置",
                "db_table": "dingtalk_config",
            },
        ),
    ]
