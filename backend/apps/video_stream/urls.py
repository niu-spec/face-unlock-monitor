from django.urls import path

from . import views


urlpatterns = [
    path("video_feed/<str:stream_id>", views.video_feed, name="video-feed"),
    path("api/video/status", views.video_status, name="video-status"),
    path(
        "api/video/streams/<str:stream_id>/source",
        views.video_source,
        name="video-source",
    ),
]
