"""Detection — URL 路由"""
from django.urls import path
from . import views

urlpatterns = [
    path("analyze/", views.analyze_frame, name="detection-analyze"),
    path("status/", views.detection_status, name="detection-status"),
    # ★ v1.3 音频检测
    path("audio/status/", views.audio_status, name="detection-audio-status"),
]