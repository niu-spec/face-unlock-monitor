"""Alerts — 视图：告警列表 + 内部创建 + 处置"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema

from apps.accounts.views import HouseholdFilterMixin
from apps.alerts.models import Alert
from apps.alerts.serializers import AlertSerializer
from apps.alerts.services import handle_alert


class AlertViewSet(HouseholdFilterMixin, viewsets.ModelViewSet):
    """
    告警管理。

    每个家庭只看到自己的告警。
    """

    queryset = Alert.objects.all()
    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        alert_type = self.request.query_params.get("type")
        alert_status = self.request.query_params.get("status")
        stream_id = self.request.query_params.get("stream_id")
        if alert_type:
            qs = qs.filter(type=alert_type)
        if alert_status:
            qs = qs.filter(status=alert_status)
        if stream_id:
            qs = qs.filter(stream_id=stream_id)
        return qs

    @swagger_auto_schema(tags=["告警管理"])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=["告警管理"],
        operation_description="创建告警 — C/D 通过此接口写入告警。需传 household_id",
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @swagger_auto_schema(tags=["告警管理"])
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=["告警管理"],
        operation_description="处置告警 — 标记为 handled",
    )
    @action(detail=True, methods=["put"])
    def handle(self, request, pk=None):
        """PUT /api/alerts/{id}/handle/ — 处置告警"""
        alert = self.get_object()
        if alert.status != "pending":
            return Response(
                {"error": "该告警已处理或已忽略"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        updated = handle_alert(alert.id)
        return Response(AlertSerializer(updated).data)
