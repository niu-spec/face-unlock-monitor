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

    后续由 AI 模块（人脸识别/人员检测）写入实时数据；
    目前返回占位数据，供前端联调。
    """
    return Response(
        {
            "total": 0,
            "family": 0,
            "stranger": 0,
        }
    )
