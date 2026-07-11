from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("alerts", "0003_add_notification_fields"),
    ]

    operations = [
        migrations.AlterField(
            model_name="alert",
            name="type",
            field=models.CharField(
                choices=[
                    ("FACE_UNKNOWN", "陌生人"),
                    ("FACE_SPOOF", "人脸欺骗攻击"),
                    ("FACE_REPLAY", "照片/视频重放攻击"),
                    ("FACE_DEEPFAKE", "AI换脸攻击"),
                    ("FACE_AUTH_FAILED", "人脸认证失败"),
                    ("INTRUSION", "区域闯入"),
                    ("PROXIMITY", "距离过近"),
                    ("LOITER", "异常停留"),
                    ("TAILGATE", "尾随进入"),
                    ("FIRE", "火情"),
                    ("WATER", "积水"),
                    ("FALL", "人员摔倒"),
                    ("SCREAM", "尖叫/呼救声"),
                    ("FIGHT", "打架/争吵声"),
                    ("CRYING", "哭喊声"),
                    ("GLASS_BREAK", "玻璃破碎声"),
                    ("ABNORMAL_SOUND", "异常声音"),
                    ("EMERGENCY", "音视频联动紧急事件"),
                ],
                max_length=32,
                verbose_name="告警类型",
            ),
        ),
        migrations.AlterField(
            model_name="alert",
            name="level",
            field=models.CharField(
                choices=[
                    ("CRITICAL", "紧急"),
                    ("HIGH", "高"),
                    ("MEDIUM", "中"),
                    ("LOW", "低"),
                ],
                default="MEDIUM",
                max_length=16,
                verbose_name="严重等级",
            ),
        ),
    ]
