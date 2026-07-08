"""Django REST Framework endpoints for face registration and analysis."""

from __future__ import annotations

import base64

import cv2
from django.db import transaction
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import FamilyMember
from apps.households.filters import resolve_active_household_id
from .services import get_face_service


def _decode_request_image(request):
    service = get_face_service()
    uploaded = request.FILES.get("image")
    if uploaded:
        return service.decode_image_bytes(uploaded.read())
    return service.decode_base64_image(request.data.get("image", ""))


class FaceRegisterView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @swagger_auto_schema(
        tags=["人脸识别"],
        operation_description="上传单人照片，提取128维编码并注册家庭成员",
        manual_parameters=[
            openapi.Parameter("member_id", openapi.IN_FORM, type=openapi.TYPE_INTEGER),
            openapi.Parameter("name", openapi.IN_FORM, type=openapi.TYPE_STRING, required=True),
            openapi.Parameter("role", openapi.IN_FORM, type=openapi.TYPE_STRING, required=True),
            openapi.Parameter("image", openapi.IN_FORM, type=openapi.TYPE_FILE, required=True),
        ],
        responses={201: "注册成功", 400: "图片或参数无效"},
    )
    def post(self, request):
        household_id = resolve_active_household_id(request)
        if not household_id:
            return Response({"error": "请先选择当前家庭"}, status=status.HTTP_400_BAD_REQUEST)
        name = str(request.data.get("name", "")).strip()
        role = str(request.data.get("role", "")).strip()
        if not name or role not in dict(FamilyMember.ROLE_CHOICES):
            return Response({"error": "name 或 role 无效"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            frame = _decode_request_image(request)
            encoding = get_face_service().encode_single_face(frame).astype(float).tolist()
            with transaction.atomic():
                member_id = request.data.get("member_id")
                if member_id:
                    member = FamilyMember.objects.get(
                        id=member_id, household_id=household_id
                    )
                    member.name = name
                    member.role = role
                else:
                    member = FamilyMember(
                        household_id=household_id, name=name, role=role
                    )
                member.face_encoding = encoding
                member.save()
                registered = get_face_service().register_encoding(
                    member.id, member.name, member.role, encoding, household_id
                )
        except FamilyMember.DoesNotExist:
            return Response({"error": "家庭成员不存在"}, status=status.HTTP_404_NOT_FOUND)
        except (ValueError, RuntimeError) as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {"success": True, "member": registered}, status=status.HTTP_201_CREATED
        )


class FaceAnalyzeView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @swagger_auto_schema(
        tags=["人脸识别"],
        operation_description="分析单张图片，返回标注图、人数统计和陌生人事件",
        manual_parameters=[
            openapi.Parameter("stream_id", openapi.IN_FORM, type=openapi.TYPE_STRING),
            openapi.Parameter("image", openapi.IN_FORM, type=openapi.TYPE_FILE, required=True),
        ],
    )
    def post(self, request):
        try:
            frame = _decode_request_image(request)
            stream_id = str(request.data.get("stream_id", "image_test"))
            household_id = resolve_active_household_id(request)
            output, presence, events = get_face_service().process_frame(
                frame, stream_id=stream_id, household_id=household_id
            )
            ok, encoded = cv2.imencode(".jpg", output, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not ok:
                raise ValueError("标注图片编码失败")
        except (ValueError, RuntimeError) as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                "success": True,
                "presence": presence,
                "events": events,
                "annotated_image": base64.b64encode(encoded).decode("ascii"),
            }
        )


class FaceMembersView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(tags=["人脸识别"], operation_description="列出特征库成员")
    def get(self, request):
        return Response(
            {"success": True, "members": get_face_service().list_registered_members()}
        )
