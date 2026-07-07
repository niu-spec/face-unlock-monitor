"""
门禁 / 危险区域模型。

前端 ZoneEditor.vue 画的多边形区域，用于：
  - 判断是否有人闯入禁区（INTRUSION）
  - 判断是否有人靠太近（PROXIMITY）
  - 判断是否异常停留（LOITER）
"""

from django.db import models


class Zone(models.Model):
    """视频画面上的多边形安防区域"""

    STREAM_CHOICES = [
        ("living_room", "客厅"),
        ("kitchen", "厨房"),
    ]

    name = models.CharField("区域名称", max_length=64)
    stream_id = models.CharField(
        "关联视频流",
        max_length=32,
        choices=STREAM_CHOICES,
        default="living_room",
    )
    points_json = models.JSONField(
        "多边形顶点",
        help_text="JSON 数组，如 [[x1,y1], [x2,y2], [x3,y3], ...]",
    )
    forbidden_roles = models.JSONField(
        "禁止进入的角色",
        default=list,
        help_text="如 ['child'] 表示小孩禁止进入该区域",
    )
    safe_distance = models.IntegerField("安全距离(px)", default=50, help_text="小于此距离触发 PROXIMITY 告警")
    dwell_time = models.IntegerField("停留阈值(秒)", default=5, help_text="停留超过此时长触发 LOITER 告警")
    is_active = models.BooleanField("启用", default=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        db_table = "zone"
        verbose_name = "安防区域"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} → {self.stream_id}"
