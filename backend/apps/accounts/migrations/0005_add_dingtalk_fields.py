# Generated migration — add DingTalk fields to User

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_remove_user_nickname"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="dingtalk_user_id",
            field=models.CharField(
                blank=True,
                default="",
                help_text="钉钉企业内部UserID，用于@提醒（非unionid）",
                max_length=128,
                verbose_name="钉钉UserID",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="dingtalk_mobile",
            field=models.CharField(
                blank=True,
                default="",
                help_text="如与登录手机号不同，用于钉钉@手机号提醒",
                max_length=16,
                verbose_name="钉钉手机号",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="supervisor",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="subordinates",
                to=settings.AUTH_USER_MODEL,
                verbose_name="直属上级",
                help_text="升级链路：当前用户未响应时，告警升级至其上级",
            ),
        ),
    ]
