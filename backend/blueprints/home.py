"""Home presence API."""

from flask_restx import Namespace, Resource

from services.face_service import get_face_service

home_ns = Namespace("home", description="家庭实时状态")


@home_ns.route("/presence")
class HomePresenceResource(Resource):
    def get(self):
        """返回最近一次人脸分析得到的总人数、家人和陌生人数。"""
        return get_face_service().get_presence()
