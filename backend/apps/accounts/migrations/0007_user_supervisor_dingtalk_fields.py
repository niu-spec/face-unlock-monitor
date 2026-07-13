from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0006_familymember_identity"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="supervisor_dingtalk_user_id",
            field=models.CharField(
                blank=True,
                default="",
                help_text="告警超时升级时 @ 的上级钉钉 UserID（无需对方注册账号）",
                max_length=128,
                verbose_name="上级钉钉UserID",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="supervisor_dingtalk_mobile",
            field=models.CharField(
                blank=True,
                default="",
                help_text="告警超时升级时 @ 的上级手机号（与 UserID 二选一或同时填）",
                max_length=16,
                verbose_name="上级钉钉手机号",
            ),
        ),
    ]
