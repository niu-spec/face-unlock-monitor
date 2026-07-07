"""
用户体系模型。

三层结构：
  - Household    → 家庭（一个家庭 = 一套摄像头系统）
  - User         → 登录账号（属于某个家庭，管理员/保安）
  - FamilyMember → 家庭成员（属于某个家庭，被摄像头识别的人）
"""

from django.contrib.auth.models import User
from django.db import models


class Household(models.Model):
    """家庭/住户 — 数据隔离的基本单位。

    每个家庭拥有独立的摄像头、家庭成员、区域、告警和事件日志。
    不同家庭之间的数据完全隔离。
    """

    name = models.CharField("家庭名称", max_length=64, unique=True, help_text="如：张三家、李四家")
    address = models.CharField("地址", max_length=256, blank=True, help_text="可选，如：3栋501")
    is_active = models.BooleanField("启用", default=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        db_table = "household"
        verbose_name = "家庭"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    """用户扩展信息 — 关联 Django User 到 Household。

    一个 User（登录账号）属于一个家庭。
    superuser (is_superuser=True) 不属于任何家庭，可以管理所有数据。
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    household = models.ForeignKey(
        Household,
        on_delete=models.CASCADE,
        related_name="users",
        verbose_name="所属家庭",
        help_text="该登录账号属于哪个家庭",
    )

    class Meta:
        db_table = "user_profile"
        verbose_name = "用户扩展"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.user.username} → {self.household.name}"


class FamilyMember(models.Model):
    """家庭成员 — 被摄像头识别的人，属于某个家庭"""

    ROLE_CHOICES = [
        ("adult", "成人"),
        ("child", "小孩"),
        ("elder", "老人"),
        ("guest", "访客"),
    ]

    household = models.ForeignKey(
        Household,
        on_delete=models.CASCADE,
        related_name="members",
        verbose_name="所属家庭",
    )
    name = models.CharField("姓名", max_length=64)
    role = models.CharField("角色", max_length=16, choices=ROLE_CHOICES, default="adult")
    student_id = models.CharField("学号/工号", max_length=32, blank=True)
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
        unique_together = [["household", "student_id"]]

    def __str__(self):
        return f"{self.name}({self.get_role_display()}) [{self.household.name}]"
