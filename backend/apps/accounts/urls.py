"""Accounts — URL 路由"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.accounts.views import login_view, FamilyMemberViewSet

router = DefaultRouter()
router.register(r"members", FamilyMemberViewSet, basename="family-member")

urlpatterns = [
    path("login/", login_view, name="auth-login"),
    path("", include(router.urls)),
]
