from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("alerts", "0004_expand_alert_type_and_level_choices"),
    ]

    operations = [
        migrations.AddField(
            model_name="alert",
            name="clip_path",
            field=models.CharField(
                blank=True,
                default="",
                help_text="告警时刻前后截取的 MP4 短视频文件名",
                max_length=256,
                verbose_name="短视频路径",
            ),
        ),
    ]
