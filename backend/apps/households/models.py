"""Household 模型 — 家庭、成员关系、加入申请、摄像头"""
from django.db import models


class Household(models.Model):
    """家庭/住户 — 数据隔离的基本单位"""

    name = models.CharField("家庭名称", max_length=64)
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="owned_households",
        verbose_name="创建者",
    )
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        db_table = "household"
        verbose_name = "家庭"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class HouseholdMembership(models.Model):
    """用户 ↔ 家庭 多对多关系"""

    ROLE_CHOICES = [
        ("admin", "管理员"),
        ("member", "成员"),
    ]

    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField("角色", max_length=16, choices=ROLE_CHOICES, default="member")
    joined_at = models.DateTimeField("加入时间", auto_now_add=True)

    class Meta:
        db_table = "household_membership"
        unique_together = [("household", "user")]
        verbose_name = "成员关系"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.user.phone} → {self.household.name} ({self.get_role_display()})"


class JoinApplication(models.Model):
    """加入家庭申请"""

    STATUS_CHOICES = [
        ("pending", "待审核"),
        ("approved", "已通过"),
        ("rejected", "已拒绝"),
    ]

    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="applications")
    applicant = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="applications")
    status = models.CharField("状态", max_length=16, choices=STATUS_CHOICES, default="pending")
    reviewer = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_applications"
    )
    message = models.CharField("申请留言", max_length=256, blank=True)
    created_at = models.DateTimeField("申请时间", auto_now_add=True)
    reviewed_at = models.DateTimeField("审核时间", null=True, blank=True)

    class Meta:
        db_table = "join_application"
        verbose_name = "加入申请"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]


class Camera(models.Model):
    """摄像头 — 归属家庭"""

    name = models.CharField("摄像头名称", max_length=64)
    household = models.ForeignKey(Household, on_delete=models.CASCADE, related_name="cameras")
    rtsp_url = models.CharField("RTSP 地址", max_length=512, blank=True)
    stream_id = models.CharField("视频流ID", max_length=32, default="living_room")
    is_active = models.BooleanField("启用", default=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        db_table = "camera"
        verbose_name = "摄像头"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} [{self.household.name}]"
