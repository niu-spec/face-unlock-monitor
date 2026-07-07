"""
家庭成员模型 — 被摄像头识别的人。

与 Django User（管理员/保安）分开：
  - User       → 登录系统、管理后台的人
  - FamilyMember → 摄像头识别出的家庭成员
"""

from django.db import models


class FamilyMember(models.Model):
    """摄像头识别对象 — 家庭成员或常客"""

    ROLE_CHOICES = [
        ("adult", "成人"),
        ("child", "小孩"),
        ("elder", "老人"),
        ("guest", "访客"),
    ]

    name = models.CharField("姓名", max_length=64)
    role = models.CharField("角色", max_length=16, choices=ROLE_CHOICES, default="adult")
    student_id = models.CharField("学号/工号", max_length=32, blank=True, unique=True)
    face_encoding = models.JSONField(
        "人脸编码(128维)",
        null=True,
        blank=True,
        help_text="dlib 提取的 128 维特征向量，JSON 数组格式",
    )
    is_active = models.BooleanField("启用", default=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        db_table = "family_member"
        verbose_name = "家庭成员"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name}({self.get_role_display()})"
