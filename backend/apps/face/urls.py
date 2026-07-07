from django.urls import path

from .views import FaceAnalyzeView, FaceMembersView, FaceRegisterView

urlpatterns = [
    path("register/", FaceRegisterView.as_view(), name="face-register"),
    path("analyze/", FaceAnalyzeView.as_view(), name="face-analyze"),
    path("members/", FaceMembersView.as_view(), name="face-members"),
]
