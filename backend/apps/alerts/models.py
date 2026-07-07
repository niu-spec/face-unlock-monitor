"""
告警模型。

告警来源：
  - C（人脸识别）→ FACE_UNKNOWN 陌生人
  - D（异常检测）→ INTRUSION / PROXIMITY / LOITER / TAILGATE / FIRE / WATER / FALL
"""

from django.db import models


class Alert(models.Model):
    """安防告警事件"""

    TYPE_CHOICES = [
        ("FACE_UNKNOWN", "陌生人"),
        ("INTRUSION", "区域闯入"),
        ("PROXIMITY", "距离过近"),
        ("LOITER", "异常停留"),
        ("TAILGATE", "尾随进入"),
        ("FIRE", "火情"),
        ("WATER", "积水"),
        ("FALL", "人员摔倒"),
    ]

    LEVEL_CHOICES = [
        ("HIGH", "高"),
        ("MEDIUM", "中"),
        ("LOW", "低"),
    ]

    STATUS_CHOICES = [
        ("pending", "待处理"),
        ("handled", "已处理"),
        ("ignored", "已忽略"),
    ]

    type = models.CharField("告警类型", max_length=32, choices=TYPE_CHOICES)
    level = models.CharField("严重等级", max_length=16, choices=LEVEL_CHOICES, default="MEDIUM")
    stream_id = models.CharField("视频流ID", max_length=32, default="living_room")
    description = models.TextField("告警描述", blank=True)
    snapshot_path = models.CharField("截图路径", max_length=256, blank=True, help_text="告警时刻的截图文件路径")
    status = models.CharField("处理状态", max_length=16, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField("发生时间", auto_now_add=True)
    handled_at = models.DateTimeField("处置时间", null=True, blank=True)

    class Meta:
        db_table = "alert"
        verbose_name = "告警"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.get_type_display()}] {self.description[:40]}"
