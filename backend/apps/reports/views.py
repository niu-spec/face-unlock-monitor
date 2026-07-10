from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema

from apps.households.filters import HouseholdFilterBackend, resolve_active_household_id
from apps.reports.models import DailyReport
from apps.reports.serializers import DailyReportGenerateSerializer, DailyReportSerializer
from apps.reports.services import generate_daily_report


class DailyReportViewSet(viewsets.ReadOnlyModelViewSet):
    """监控日报 — 按家庭查看 / 触发生成。"""

    queryset = DailyReport.objects.all()
    serializer_class = DailyReportSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [HouseholdFilterBackend]

    @swagger_auto_schema(tags=["监控日报"])
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(tags=["监控日报"])
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        tags=["监控日报"],
        operation_description="按日期生成或刷新 AI 监控日报（默认今天）",
        request_body=DailyReportGenerateSerializer,
    )
    @action(detail=False, methods=["post"], url_path="generate")
    def generate(self, request):
        household_id = resolve_active_household_id(request)
        if not household_id:
            return Response(
                {"error": "请先选择活跃家庭（X-Active-Household-Id）"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload = DailyReportGenerateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        report_date = payload.validated_data.get("date")

        report = generate_daily_report(household_id, report_date)
        return Response(
            DailyReportSerializer(report).data,
            status=status.HTTP_200_OK,
        )
