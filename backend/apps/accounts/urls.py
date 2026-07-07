"""Accounts — URL 路由"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.accounts.views import (
    login_view, register_view, send_sms_view, captcha_view, me_view,
    FamilyMemberViewSet,
)

router = DefaultRouter()
router.register(r"members", FamilyMemberViewSet, basename="family-member")

urlpatterns = [
    path("login/", login_view, name="auth-login"),
    path("register/", register_view, name="auth-register"),
    path("sms/send/", send_sms_view, name="auth-sms-send"),
    path("captcha/", captcha_view, name="auth-captcha"),
    path("me/", me_view, name="auth-me"),
    path("", include(router.urls)),
]
