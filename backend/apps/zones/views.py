"""Zones — 视图：危险区域 CRUD"""
from rest_framework import viewsets
from drf_yasg.utils import swagger_auto_schema
from apps.zones.models import Zone
from apps.zones.serializers import ZoneSerializer


class ZoneViewSet(viewsets.ModelViewSet):
    """
    安防区域管理 — CRUD。

    前端 ZoneEditor.vue 配合使用：
    - 在视频画面上画多边形定义危险区域
    - 设置哪些角色禁止进入（如 child）
    - 设置安全距离和停留时间阈值
    """

    queryset = Zone.objects.filter(is_active=True)
    serializer_class = ZoneSerializer

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
