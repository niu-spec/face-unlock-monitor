"""Accounts — URL 路由"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.accounts.views import (
    login_view, logout_view, register_view, send_sms_view, captcha_view, me_view, profile_view, update_profile_view, change_phone_view,
    FamilyMemberViewSet,
)

router = DefaultRouter()
router.register(r"members", FamilyMemberViewSet, basename="family-member")

urlpatterns = [
    path("login/", login_view, name="auth-login"),
    path("logout/", logout_view, name="auth-logout"),
    path("register/", register_view, name="auth-register"),
    path("sms/send/", send_sms_view, name="auth-sms-send"),
    path("captcha/", captcha_view, name="auth-captcha"),
    path("me/", me_view, name="auth-me"),
    path("profile/", profile_view, name="auth-profile"),
    path("profile/update/", update_profile_view, name="auth-profile-update"),
    path("change-phone/", change_phone_view, name="auth-change-phone"),
    path("", include(router.urls)),
]
