from django.contrib import admin

from apps.reports.models import DailyReport


@admin.register(DailyReport)
class DailyReportAdmin(admin.ModelAdmin):
    list_display = ("report_date", "household", "source", "title", "updated_at")
    list_filter = ("source", "report_date")
    search_fields = ("title", "summary")
    readonly_fields = ("created_at", "updated_at")
