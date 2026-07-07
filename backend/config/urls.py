"""Root URL configuration with Swagger."""
from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
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
    path("api/detection/", include("apps.detection.urls")),  # D-李东礼

    # Swagger / OpenAPI
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]
