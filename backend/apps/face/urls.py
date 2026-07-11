from django.urls import path

from .views import FaceAnalyzeView, FaceLivenessView, FaceMembersView, FaceRegisterView

urlpatterns = [
    path("register/", FaceRegisterView.as_view(), name="face-register"),
    path("liveness/", FaceLivenessView.as_view(), name="face-liveness"),
    path("analyze/", FaceAnalyzeView.as_view(), name="face-analyze"),
    path("members/", FaceMembersView.as_view(), name="face-members"),
]
