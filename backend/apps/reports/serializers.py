from rest_framework import serializers

from apps.reports.models import DailyReport


class DailyReportSerializer(serializers.ModelSerializer):
    source_display = serializers.CharField(source="get_source_display", read_only=True)

    class Meta:
        model = DailyReport
        fields = [
            "id",
            "report_date",
            "title",
            "summary",
            "stats",
            "source",
            "source_display",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class DailyReportGenerateSerializer(serializers.Serializer):
    date = serializers.DateField(required=False)
