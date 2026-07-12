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
from .liveness import get_liveness_service
from .services import get_face_service


def _decode_request_image(request):
    service = get_face_service()
    uploaded = request.FILES.get("image")
    if uploaded:
        return service.decode_image_bytes(uploaded.read())
    return service.decode_base64_image(request.data.get("image", ""))


def _decode_request_images(request) -> list:
    service = get_face_service()
    frames = []
    uploaded_files = request.FILES.getlist("images") or request.FILES.getlist("image")
    for uploaded in uploaded_files:
        frames.append(service.decode_image_bytes(uploaded.read()))

    images = request.data.get("images")
    if isinstance(images, list):
        frames.extend(service.decode_base64_image(value) for value in images)

    if not frames:
        frames.append(_decode_request_image(request))
    return frames


def _presence_for_frames(frames: list, stream_id: str, household_id: int | None) -> list[dict]:
    service = get_face_service()
    presences = []
    for frame in frames:
        _output, presence, _events = service.process_frame(
            frame,
            stream_id=stream_id,
            household_id=household_id,
            annotate=False,
            persist_alert=False,
        )
        presences.append(presence)
    return presences


def _best_registration_frame(frames: list, presences: list[dict]):
    best_index = 0
    best_area = -1
    for index, presence in enumerate(presences):
        for face in presence.get("faces") or []:
            box = face.get("box") or {}
            area = max(0, int(box.get("right", 0)) - int(box.get("left", 0))) * max(
                0, int(box.get("bottom", 0)) - int(box.get("top", 0))
            )
            if area > best_area:
                best_area = area
                best_index = index
    return frames[best_index]


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
        consumes=["multipart/form-data"],
    )
    def post(self, request):
        household_id = resolve_active_household_id(request)
        if not household_id:
            return Response({"error": "请先选择当前家庭"}, status=status.HTTP_400_BAD_REQUEST)
        name = str(request.data.get("name", "")).strip()
        identity = str(request.data.get("identity", "")).strip()
        role = str(request.data.get("role", "")).strip()
        if not name or role not in dict(FamilyMember.ROLE_CHOICES):
            return Response({"error": "name 或 role 无效"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            frames = _decode_request_images(request)
            frame = frames[0]
            liveness_result = None
            if len(frames) >= 3:
                presences = _presence_for_frames(frames, "face_register", household_id)
                liveness_result = get_liveness_service().analyze_sequence(
                    frames, presences, stream_id="face_register"
                )
                if not liveness_result.get("passed"):
                    return Response(
                        {
                            "error": "活体检测未通过",
                            "attack_type": liveness_result.get("attack_type"),
                            "reason": liveness_result.get("reason"),
                            "liveness": liveness_result,
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                frame = _best_registration_frame(frames, presences)
            encoding = get_face_service().encode_single_face(frame).astype(float).tolist()
            with transaction.atomic():
                member_id = request.data.get("member_id")
                if member_id:
                    member = FamilyMember.objects.get(
                        id=member_id, household_id=household_id
                    )
                    member.name = name
                    member.identity = identity
                    member.role = role
                else:
                    member = FamilyMember(
                        household_id=household_id, name=name, identity=identity, role=role
                    )
                member.face_encoding = encoding
                member.save()
                registered = get_face_service().register_encoding(
                    member.id, member.name, member.role, encoding, household_id,
                    identity=member.identity,
                )
        except FamilyMember.DoesNotExist:
            return Response({"error": "家庭成员不存在"}, status=status.HTTP_404_NOT_FOUND)
        except (ValueError, RuntimeError) as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {"success": True, "member": registered, "liveness": liveness_result},
            status=status.HTTP_201_CREATED,
        )


class FaceLivenessView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @swagger_auto_schema(
        tags=["face"],
        operation_description="Run passive liveness detection on 3-5 face frames.",
        manual_parameters=[
            openapi.Parameter("stream_id", openapi.IN_FORM, type=openapi.TYPE_STRING),
            openapi.Parameter("images", openapi.IN_FORM, type=openapi.TYPE_FILE, required=True),
        ],
        consumes=["multipart/form-data"],
    )
    def post(self, request):
        try:
            frames = _decode_request_images(request)
            stream_id = str(request.data.get("stream_id", "auth"))
            household_id = resolve_active_household_id(request)
            presences = _presence_for_frames(frames, stream_id, household_id)
            result = get_liveness_service().analyze_sequence(frames, presences, stream_id=stream_id)
        except (ValueError, RuntimeError) as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"success": True, "liveness": result, "presence": presences[-1] if presences else None})


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
        consumes=["multipart/form-data"],
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
