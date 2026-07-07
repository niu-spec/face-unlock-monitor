"""Home — URL 路由"""
from django.urls import path
from apps.home.views import presence_view

urlpatterns = [
    path("presence/", presence_view, name="home-presence"),
]
