from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0002_event_snapshot_and_alert_types"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="clip_path",
            field=models.CharField(
                blank=True,
                default="",
                help_text="事件时刻 MP4 短视频文件名",
                max_length=256,
                verbose_name="短视频路径",
            ),
        ),
    ]
