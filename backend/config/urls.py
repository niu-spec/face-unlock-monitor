"""Root URL configuration with Swagger."""
from django.contrib import admin
from django.urls import path, include
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework.permissions import AllowAny

from apps.events.replay_views import clip_file, snapshot_file

schema_view = get_schema_view(
    openapi.Info(
        title="Home Camera Monitor API",
        default_version="v1.0",
        description="居家智能摄像头监控系统 — 业务 API 文档",
    ),
    public=True,
    permission_classes=[AllowAny],
)

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),

    # API v1
    path("api/auth/", include("apps.accounts.urls")),
    path("api/home/", include("apps.home.urls")),
    path("api/zones/", include("apps.zones.urls")),
    path("api/alerts/", include("apps.alerts.urls")),
    path("api/events/", include("apps.events.urls")),
    path("api/reports/", include("apps.reports.urls")),
    path("api/snapshots/<str:filename>/", snapshot_file, name="snapshot-replay"),
    path("api/clips/<str:filename>/", clip_file, name="clip-replay"),
    path("api/detection/", include("apps.detection.urls")),
    path("api/face/", include("apps.face.urls")),
    path("", include("apps.video_stream.urls")),  # 视频流
    path("api/", include("apps.households.urls")),  # 家庭 / 摄像头

    path("api/notifications/", include("apps.notifications.urls")),

    # Swagger UI
    path(
        "api/docs/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="swagger-ui",
    ),
]
