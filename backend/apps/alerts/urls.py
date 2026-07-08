"""Alerts — URL 路由"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.alerts.views import AlertViewSet

router = DefaultRouter()
router.register(r"", AlertViewSet, basename="alert")

urlpatterns = [
    path("", include(router.urls)),
]
