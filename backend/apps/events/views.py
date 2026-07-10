"""Events — 视图：事件日志查询"""
from rest_framework import viewsets, mixins
from drf_yasg.utils import swagger_auto_schema
from apps.households.filters import HouseholdFilterBackend
from apps.events.models import Event
from apps.events.serializers import EventSerializer


class EventViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """事件日志 — 按家庭过滤（只读）"""

    queryset = Event.objects.all()
    serializer_class = EventSerializer
    filter_backends = [HouseholdFilterBackend]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Event.objects.none()
        qs = super().get_queryset()
        event_type = self.request.query_params.get("event_type")
        stream_id = self.request.query_params.get("stream_id")
        if event_type:
            qs = qs.filter(event_type=event_type)
        if stream_id:
            qs = qs.filter(stream_id=stream_id)
        return qs

    @swagger_auto_schema(tags=["事件日志"])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(tags=["事件日志"])
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
