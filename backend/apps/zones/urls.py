"""Zones — URL 路由"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.zones.views import ZoneViewSet

router = DefaultRouter()
router.register(r"", ZoneViewSet, basename="zone")

urlpatterns = [
    path("", include(router.urls)),
]
