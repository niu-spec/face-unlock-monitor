"""
告警模型。

告警来源：
  - C（人脸识别）→ FACE_UNKNOWN 陌生人
  - D（异常检测）→ INTRUSION / PROXIMITY / LOITER / TAILGATE / FIRE / FALL
  - WATER 积水已下线，choices 仅保留兼容历史数据
"""

from django.db import models


class Alert(models.Model):
    """安防告警事件"""

    TYPE_CHOICES = [
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
        # 音频异常检测（v1.3）
        ("SCREAM", "尖叫/呼救声"),
        ("FIGHT", "打架/争吵声"),
        ("CRYING", "哭喊声"),
        ("GLASS_BREAK", "玻璃破碎声"),
        ("ABNORMAL_SOUND", "异常声音"),
        ("EMERGENCY", "音视频联动紧急事件"),
    ]

    LEVEL_CHOICES = [
        ("CRITICAL", "紧急"),
        ("HIGH", "高"),
        ("MEDIUM", "中"),
        ("LOW", "低"),
    ]

    STATUS_CHOICES = [
        ("pending", "待处理"),
        ("handled", "已处理"),
        ("ignored", "已忽略"),
    ]

    household = models.ForeignKey(
        "households.Household", on_delete=models.CASCADE, related_name="alerts",
        verbose_name="所属家庭", null=True,
    )
    type = models.CharField("告警类型", max_length=32, choices=TYPE_CHOICES)
    level = models.CharField("严重等级", max_length=16, choices=LEVEL_CHOICES, default="MEDIUM")
    stream_id = models.CharField("视频流ID", max_length=32, default="living_room")
    description = models.TextField("告警描述", blank=True)
    snapshot_path = models.CharField("截图路径", max_length=256, blank=True, help_text="告警时刻的截图文件路径")
    clip_path = models.CharField(
        "短视频路径",
        max_length=256,
        blank=True,
        default="",
        help_text="告警时刻前后截取的 MP4 短视频文件名",
    )
    status = models.CharField("处理状态", max_length=16, choices=STATUS_CHOICES, default="pending")
    assigned_to = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="assigned_alerts", verbose_name="当前负责人",
        help_text="当前应处理此告警的人（升级后指向上级）",
    )
    escalation_level = models.IntegerField(
        "升级层级", default=0,
        help_text="0=主R, 1=+1上级, 2=+2上级...",
    )
    escalation_last_at = models.DateTimeField(
        "最近升级时间", null=True, blank=True,
        help_text="上一次触发升级的时间",
    )
    notified_at = models.DateTimeField(
        "首次通知时间", null=True, blank=True,
        help_text="告警首次推送到钉钉的时间",
    )
    metadata = models.JSONField(
        "扩展元数据", default=dict, blank=True,
        help_text="存储通知历史、升级记录等扩展信息",
    )
    created_at = models.DateTimeField("发生时间", auto_now_add=True)
    handled_at = models.DateTimeField("处置时间", null=True, blank=True)

    class Meta:
        db_table = "alert"
        verbose_name = "告警"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.get_type_display()}] {self.description[:40]}"
