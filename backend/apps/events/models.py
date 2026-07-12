"""
事件日志模型 — 记录系统运行过程中的关键事件。

如：人脸识别成功、门锁操作、系统启动等。
"""

from django.db import models


class Event(models.Model):
    """系统事件日志"""

    TYPE_CHOICES = [
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
    ]

    household = models.ForeignKey(
        "households.Household", on_delete=models.CASCADE, related_name="events",
        verbose_name="所属家庭", null=True,
    )
    event_type = models.CharField("事件类型", max_length=32, choices=TYPE_CHOICES)
    stream_id = models.CharField("视频流ID", max_length=32, default="living_room")
    description = models.CharField("事件描述", max_length=256)
    snapshot_path = models.CharField(
        "截图路径",
        max_length=256,
        blank=True,
        default="",
        help_text="事件时刻截图文件名",
    )
    clip_path = models.CharField(
        "短视频路径",
        max_length=256,
        blank=True,
        default="",
        help_text="事件时刻 MP4 短视频文件名",
    )
    metadata = models.JSONField("附加数据", default=dict, blank=True, help_text="如识别到的成员ID、姓名等")
    created_at = models.DateTimeField("发生时间", auto_now_add=True)

    class Meta:
        db_table = "event_log"
        verbose_name = "事件日志"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.get_event_type_display()}] {self.description}"
