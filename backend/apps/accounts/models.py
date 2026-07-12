"""
用户体系模型。

  - User(AbstractUser)  → 手机号注册登录
  - SmsVerificationCode → 短信验证码
  - Captcha            → 数学验证码
  - FamilyMember       → 家庭成员（被摄像头识别）
"""

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError("手机号必填")
        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(phone, password, **extra_fields)


class User(AbstractUser):
    """自定义用户 — 手机号登录"""

    username = None
    phone = models.CharField("手机号", max_length=16, unique=True, db_index=True)

    dingtalk_user_id = models.CharField(
        "钉钉UserID", max_length=128, blank=True, default="",
        help_text="钉钉企业内部UserID，用于@提醒（非unionid）",
    )
    supervisor = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="subordinates", verbose_name="直属上级",
        help_text="升级链路：当前用户未响应时，告警升级至其上级",
    )
    dingtalk_mobile = models.CharField(
        "钉钉手机号", max_length=16, blank=True, default="",
        help_text="如与登录手机号不同，用于钉钉@手机号提醒",
    )

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        db_table = "accounts_user"
        verbose_name = "用户"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.phone


class SmsVerificationCode(models.Model):
    """短信验证码 — 5 分钟有效"""

    phone = models.CharField(max_length=16, db_index=True)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        db_table = "sms_verification_code"
        ordering = ["-created_at"]

    def is_valid(self):
        return not self.is_used and self.expires_at > timezone.now()


class Captcha(models.Model):
    """数学 CAPTCHA"""

    question = models.CharField(max_length=64)
    answer = models.CharField(max_length=16)
    session_key = models.CharField(max_length=64, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    class Meta:
        db_table = "captcha"
        ordering = ["-created_at"]


class FamilyMember(models.Model):
    """家庭成员 — 被摄像头识别的人"""

    ROLE_CHOICES = [
        ("adult", "成人"),
        ("child", "小孩"),
        ("elder", "老人"),
        ("guest", "访客"),
    ]

    household = models.ForeignKey(
        "households.Household",
        on_delete=models.CASCADE,
        related_name="members",
        verbose_name="所属家庭",
        null=True,
    )
    name = models.CharField("姓名", max_length=64)
    identity = models.CharField("身份", max_length=32, blank=True, default="")
    role = models.CharField("角色", max_length=16, choices=ROLE_CHOICES, default="adult")
    student_id = models.CharField("学号/工号", max_length=32, blank=True)
    face_encoding = models.JSONField("人脸编码(128维)", null=True, blank=True)
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
