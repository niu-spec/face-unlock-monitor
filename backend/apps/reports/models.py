"""AI 监控日报 — 按家庭、按日持久化。"""

from django.db import models


class DailyReport(models.Model):
    SOURCE_CHOICES = [
        ("template", "规则模板"),
        ("ai", "大模型"),
    ]

    household = models.ForeignKey(
        "households.Household",
        on_delete=models.CASCADE,
        related_name="daily_reports",
        verbose_name="所属家庭",
    )
    report_date = models.DateField("日报日期")
    title = models.CharField("标题", max_length=128)
    summary = models.TextField("日报正文（Markdown）")
    stats = models.JSONField("统计数据", default=dict, blank=True)
    source = models.CharField(
        "生成方式",
        max_length=16,
        choices=SOURCE_CHOICES,
        default="template",
    )
    created_at = models.DateTimeField("生成时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        db_table = "daily_report"
        verbose_name = "监控日报"
        verbose_name_plural = verbose_name
        ordering = ["-report_date", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["household", "report_date"],
                name="uniq_daily_report_household_date",
            )
        ]

    def __str__(self):
        return f"{self.title} ({self.report_date})"
