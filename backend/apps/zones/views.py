"""Zones — 视图：危险区域 CRUD"""
from rest_framework import viewsets
from drf_yasg.utils import swagger_auto_schema
from apps.households.filters import HouseholdFilterBackend, resolve_active_household_id
from apps.video_stream.services import clear_zone_metadata_cache
from apps.zones.models import Zone
from apps.zones.serializers import ZoneSerializer


class ZoneViewSet(viewsets.ModelViewSet):
    """安防区域管理 — 按家庭过滤"""

    queryset = Zone.objects.filter(is_active=True)
    serializer_class = ZoneSerializer
    filter_backends = [HouseholdFilterBackend]

    def perform_create(self, serializer):
        household_id = resolve_active_household_id(self.request)
        if not household_id:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"error": "请先选择当前家庭"})
        serializer.save(household_id=household_id)
        clear_zone_metadata_cache()

    def perform_update(self, serializer):
        serializer.save()
        clear_zone_metadata_cache()

    def perform_destroy(self, instance):
        instance.delete()
        clear_zone_metadata_cache()

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
