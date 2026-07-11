"""Home — 居家监控相关接口（人数统计等）"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema


@swagger_auto_schema(
    method="get",
    tags=["居家监控"],
    operation_description="当前画面人数统计",
)
@api_view(["GET"])
@permission_classes([AllowAny])
def presence_view(request):
    """
    当前画面人数统计。

    由人脸识别模块实时更新；尚未收到视频帧时返回零值。
    支持 ?stream_id= 查询指定摄像头（视频层 1/2 或业务层 living_room/kitchen）。
    """
    from apps.face.services import get_face_service
    from apps.video_stream.services import resolve_presence_stream_id

    stream_id = resolve_presence_stream_id(request.GET.get("stream_id"))
    return Response(get_face_service().get_presence(stream_id))
