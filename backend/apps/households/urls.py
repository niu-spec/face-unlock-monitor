"""Households — URL 路由"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import HouseholdViewSet, CameraViewSet

router = DefaultRouter()
router.register(r"households", HouseholdViewSet, basename="household")
router.register(r"cameras", CameraViewSet, basename="camera")

urlpatterns = [
    path("", include(router.urls)),
]
