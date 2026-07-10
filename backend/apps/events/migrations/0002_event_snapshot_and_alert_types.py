from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="snapshot_path",
            field=models.CharField(
                blank=True,
                default="",
                help_text="事件时刻截图文件名",
                max_length=256,
                verbose_name="截图路径",
            ),
        ),
        migrations.AlterField(
            model_name="event",
            name="event_type",
            field=models.CharField(
                choices=[
                    ("FACE_MATCHED", "人脸识别成功"),
                    ("FACE_UNKNOWN", "陌生人出现"),
                    ("INTRUSION", "区域闯入"),
                    ("PROXIMITY", "距离过近"),
                    ("LOITER", "异常停留"),
                    ("TAILGATE", "尾随"),
                    ("FIRE", "火情"),
                    ("WATER", "积水"),
                    ("FALL", "人员摔倒"),
                    ("LOCK", "上锁"),
                    ("SYSTEM", "系统事件"),
                ],
                max_length=32,
                verbose_name="事件类型",
            ),
        ),
    ]
