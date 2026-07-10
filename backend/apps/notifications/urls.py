"""
通知 API 路由。
"""

from django.urls import path

from apps.notifications.views import DingTalkConfigViewSet

dingtalk_config_view = DingTalkConfigViewSet.as_view({"get": "list", "put": "update"})

urlpatterns = [
    path(
        "config/",
        dingtalk_config_view,
        name="dingtalk-config",
    ),
    path(
        "config/test/",
        DingTalkConfigViewSet.as_view({"post": "test"}),
        name="dingtalk-test",
    ),
]
