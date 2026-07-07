"""Events — 视图：事件日志查询"""
from rest_framework import viewsets, mixins
from drf_yasg.utils import swagger_auto_schema
from apps.events.models import Event
from apps.events.serializers import EventSerializer


class EventViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    事件日志 — 只读查询。

    记录系统运行过程中的关键事件：
    - 人脸识别成功 / 陌生人出现
    - 区域闯入 / 过近 / 停留 / 尾随
    - 上锁操作
    - 系统事件

    GET /api/events/          — 事件列表（按时间倒序）
    GET /api/events/{id}/     — 事件详情
    """

    queryset = Event.objects.all()
    serializer_class = EventSerializer

    def get_queryset(self):
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
