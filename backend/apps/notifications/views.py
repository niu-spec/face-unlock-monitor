"""
通知 API 视图。
"""

import logging

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.households.models import HouseholdMembership
from apps.notifications.models import DingTalkConfig
from apps.notifications.serializers import DingTalkConfigSerializer

logger = logging.getLogger(__name__)


class DingTalkConfigViewSet(viewsets.GenericViewSet):
    """钉钉通知配置管理

    - GET  /api/notifications/config/     获取当前家庭的配置
    - PUT  /api/notifications/config/     更新当前家庭的配置
    - POST /api/notifications/config/test/ 发送测试消息
    """

    permission_classes = [IsAuthenticated]
    serializer_class = DingTalkConfigSerializer

    def _resolve_household_id(self):
        """获取当前家庭 ID，优先级：
        1. X-Active-Household-Id 请求头
        2. 用户的第一个家庭（自动选择）
        """
        hid = getattr(self.request, "active_household_id", None)
        if hid:
            return hid
        # 自动选择用户第一个家庭
        membership = HouseholdMembership.objects.filter(
            user=self.request.user,
        ).select_related("household").first()
        if membership:
            # 同步设置到 request，后续流程可用
            self.request.active_household_id = membership.household_id
            return membership.household_id
        return None

    def _get_or_create_config(self):
        """获取当前家庭的配置，不存在则自动创建空配置。"""
        household_id = self._resolve_household_id()
        if not household_id:
            return DingTalkConfig(is_enabled=False), False
        config, created = DingTalkConfig.objects.get_or_create(
            household_id=household_id,
            defaults={"is_enabled": False},
        )
        return config, created

    def _is_household_admin(self) -> bool:
        household_id = self._resolve_household_id()
        if not household_id:
            return False
        return HouseholdMembership.objects.filter(
            household_id=household_id,
            user=self.request.user,
            role="admin",
        ).exists()

    def list(self, request):
        config, _ = self._get_or_create_config()
        serializer = self.get_serializer(config)
        return Response(serializer.data)

    def update(self, request, pk=None):
        if not self._resolve_household_id():
            return Response(
                {"error": "你还没有加入任何家庭，请先创建家庭"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not self._is_household_admin():
            return Response(
                {"error": "仅家庭管理员可修改通知配置"},
                status=status.HTTP_403_FORBIDDEN,
            )

        config, _ = self._get_or_create_config()
        serializer = self.get_serializer(config, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def test(self, request):
        config, _ = self._get_or_create_config()

        if not config or not config.webhook_url:
            return Response(
                {"error": "请先保存 Webhook 地址后再测试"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.notifications.dingtalk import DingTalkClient

        client = DingTalkClient(config.webhook_url, config.secret or "")
        response = client.send_markdown(
            title="测试消息 - 居家监控",
            text="✅ 钉钉通知配置成功！\n\n这是一条测试消息，告警通知将以此格式发送到本群。",
        )

        if response.get("errcode") == 0:
            return Response({"message": "测试消息发送成功", "response": response})
        return Response(
            {"error": "测试消息发送失败", "response": response},
            status=status.HTTP_502_BAD_GATEWAY,
        )
