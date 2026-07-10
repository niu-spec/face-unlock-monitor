import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("households", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="DailyReport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("report_date", models.DateField(verbose_name="日报日期")),
                ("title", models.CharField(max_length=128, verbose_name="标题")),
                ("summary", models.TextField(verbose_name="日报正文（Markdown）")),
                ("stats", models.JSONField(blank=True, default=dict, verbose_name="统计数据")),
                (
                    "source",
                    models.CharField(
                        choices=[("template", "规则模板"), ("ai", "大模型")],
                        default="template",
                        max_length=16,
                        verbose_name="生成方式",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="生成时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
                (
                    "household",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="daily_reports",
                        to="households.household",
                        verbose_name="所属家庭",
                    ),
                ),
            ],
            options={
                "verbose_name": "监控日报",
                "verbose_name_plural": "监控日报",
                "db_table": "daily_report",
                "ordering": ["-report_date", "-id"],
            },
        ),
        migrations.AddConstraint(
            model_name="dailyreport",
            constraint=models.UniqueConstraint(
                fields=("household", "report_date"),
                name="uniq_daily_report_household_date",
            ),
        ),
    ]
