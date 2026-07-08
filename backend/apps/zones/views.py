"""Zones — 视图：危险区域 CRUD"""
from rest_framework import viewsets
from drf_yasg.utils import swagger_auto_schema
from apps.households.filters import HouseholdFilterBackend
from apps.zones.models import Zone
from apps.zones.serializers import ZoneSerializer


class ZoneViewSet(viewsets.ModelViewSet):
    """安防区域管理 — 按家庭过滤"""

    queryset = Zone.objects.filter(is_active=True)
    serializer_class = ZoneSerializer
    filter_backends = [HouseholdFilterBackend]

    def perform_create(self, serializer):
        serializer.save(household_id=self.request.active_household_id)

    @swagger_auto_schema(tags=["安防区域"])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(tags=["安防区域"])
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(tags=["安防区域"])
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(tags=["安防区域"])
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @swagger_auto_schema(tags=["安防区域"])
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @swagger_auto_schema(tags=["安防区域"])
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
