# Generated migration — add notification/escalation fields to Alert

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("alerts", "0002_add_face_attack_alert_types"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="alert",
            name="assigned_to",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="assigned_alerts",
                to=settings.AUTH_USER_MODEL,
                verbose_name="当前负责人",
                help_text="当前应处理此告警的人（升级后指向上级）",
            ),
        ),
        migrations.AddField(
            model_name="alert",
            name="escalation_level",
            field=models.IntegerField(
                default=0,
                verbose_name="升级层级",
                help_text="0=主R, 1=+1上级, 2=+2上级...",
            ),
        ),
        migrations.AddField(
            model_name="alert",
            name="escalation_last_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="最近升级时间",
                help_text="上一次触发升级的时间",
            ),
        ),
        migrations.AddField(
            model_name="alert",
            name="notified_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="首次通知时间",
                help_text="告警首次推送到钉钉的时间",
            ),
        ),
        migrations.AddField(
            model_name="alert",
            name="metadata",
            field=models.JSONField(
                blank=True,
                default=dict,
                verbose_name="扩展元数据",
                help_text="存储通知历史、升级记录等扩展信息",
            ),
        ),
    ]
