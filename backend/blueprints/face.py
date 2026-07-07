"""Swagger-enabled face registration and single-frame analysis API."""

import base64

import cv2
from flask import request
from flask_restx import Namespace, Resource, fields

from services.face_service import get_face_service

face_ns = Namespace("face", description="家庭成员注册与人脸识别")
service = get_face_service()

register_model = face_ns.model(
    "FaceRegisterRequest",
    {
        "member_id": fields.String(required=True, description="家庭成员唯一编号"),
        "name": fields.String(required=True, description="姓名"),
        "role": fields.String(required=True, description="角色，如 parent/child"),
        "image": fields.String(required=True, description="Base64 图片或 data URL"),
    },
)


@face_ns.route("/register")
class FaceRegisterResource(Resource):
    @face_ns.expect(register_model, validate=False)
    @face_ns.response(201, "注册成功")
    @face_ns.response(400, "请求或图片无效")
    def post(self):
        """注册或更新家庭成员的人脸特征。"""
        try:
            if request.files.get("image"):
                frame = service.decode_image_bytes(request.files["image"].read())
                data = request.form
            else:
                data = request.get_json(silent=True) or {}
                frame = service.decode_base64_image(data.get("image", ""))
            member = service.register_member(
                data.get("member_id", ""),
                data.get("name", ""),
                data.get("role", ""),
                frame,
            )
        except ValueError as exc:
            return {"success": False, "error": str(exc)}, 400
        return {"success": True, "member": member}, 201


@face_ns.route("/analyze")
class FaceAnalyzeResource(Resource):
    @face_ns.response(200, "识别成功")
    @face_ns.response(400, "图片无效")
    def post(self):
        """分析上传的单帧图片，返回标注图、人数和告警事件。"""
        try:
            stream_id = request.form.get("stream_id", "default")
            if request.files.get("image"):
                frame = service.decode_image_bytes(request.files["image"].read())
            else:
                data = request.get_json(silent=True) or {}
                stream_id = str(data.get("stream_id", "default"))
                frame = service.decode_base64_image(data.get("image", ""))
            output, presence, events = service.process_frame(frame, stream_id)
            ok, encoded = cv2.imencode(".jpg", output, [cv2.IMWRITE_JPEG_QUALITY, 75])
            if not ok:
                raise ValueError("处理结果编码失败")
        except ValueError as exc:
            return {"success": False, "error": str(exc)}, 400
        return {
            "success": True,
            "presence": presence,
            "events": events,
            "annotated_image": base64.b64encode(encoded).decode("ascii"),
        }


@face_ns.route("/members")
class FaceMembersResource(Resource):
    def get(self):
        """列出已注册家庭成员（不返回128维隐私特征）。"""
        return {"success": True, "members": service.list_members()}


@face_ns.route("/alerts")
class FaceAlertsResource(Resource):
    def get(self):
        """返回最近的陌生人告警，供告警中心或业务模块接入。"""
        return {"success": True, "alerts": service.get_recent_alerts()}
