"""监控日报 AI 工作流：采集 → 统计 → 生成 → 落库。"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from datetime import date, datetime, time, timedelta
from typing import Any

from django.db.models import Count
from django.utils import timezone

from apps.alerts.models import Alert
from apps.events.models import Event
from apps.reports.models import DailyReport

logger = logging.getLogger(__name__)

STREAM_LABELS = {
    "living_room": "客厅",
    "kitchen": "厨房",
    "1": "客厅",
    "2": "厨房",
}

ALERT_LABELS = dict(Alert.TYPE_CHOICES)
EVENT_LABELS = dict(Event.TYPE_CHOICES)


def _day_range(report_date: date) -> tuple[datetime, datetime]:
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(report_date, time.min), tz)
    end = start + timedelta(days=1)
    return start, end


def collect_daily_stats(household_id: int, report_date: date) -> dict[str, Any]:
    """汇总指定家庭、指定自然日的告警与事件数据。"""
    start, end = _day_range(report_date)

    alerts_qs = Alert.objects.filter(
        household_id=household_id,
        created_at__gte=start,
        created_at__lt=end,
    )
    events_qs = Event.objects.filter(
        household_id=household_id,
        created_at__gte=start,
        created_at__lt=end,
    )

    alerts_by_type = {
        row["type"]: row["count"]
        for row in alerts_qs.values("type").annotate(count=Count("id"))
    }
    events_by_type = {
        row["event_type"]: row["count"]
        for row in events_qs.values("event_type").annotate(count=Count("id"))
    }
    alerts_by_stream = {
        row["stream_id"]: row["count"]
        for row in alerts_qs.values("stream_id").annotate(count=Count("id"))
    }

    total_alerts = alerts_qs.count()
    pending_alerts = alerts_qs.filter(status="pending").count()
    handled_alerts = alerts_qs.filter(status="handled").count()
    high_alerts = alerts_qs.filter(level="HIGH").count()

    highlights = list(
        alerts_qs.order_by("-created_at").values(
            "type", "level", "stream_id", "description", "created_at"
        )[:8]
    )
    for item in highlights:
        item["type_label"] = ALERT_LABELS.get(item["type"], item["type"])
        item["stream_label"] = STREAM_LABELS.get(item["stream_id"], item["stream_id"])
        item["created_at"] = timezone.localtime(item["created_at"]).strftime(
            "%H:%M:%S"
        )

    return {
        "report_date": report_date.isoformat(),
        "household_id": household_id,
        "total_alerts": total_alerts,
        "pending_alerts": pending_alerts,
        "handled_alerts": handled_alerts,
        "high_alerts": high_alerts,
        "total_events": events_qs.count(),
        "alerts_by_type": alerts_by_type,
        "events_by_type": events_by_type,
        "alerts_by_stream": alerts_by_stream,
        "highlights": highlights,
    }


def _format_type_lines(mapping: dict[str, int], labels: dict[str, str]) -> str:
    if not mapping:
        return "- 无"
    lines = []
    for key, count in sorted(mapping.items(), key=lambda item: (-item[1], item[0])):
        label = labels.get(key, key)
        lines.append(f"- {label}：{count} 次")
    return "\n".join(lines)


def build_template_report(stats: dict[str, Any]) -> str:
    """规则模板生成 Markdown 日报（无 LLM 时默认使用）。"""
    report_date = stats["report_date"]
    total = stats["total_alerts"]
    pending = stats["pending_alerts"]
    handled = stats["handled_alerts"]
    high = stats["high_alerts"]

    if total == 0:
        risk = "今日整体平稳，未产生安防告警。"
        advice = "建议保持摄像头与推流在线，继续例行巡检。"
    elif pending > 0:
        risk = f"仍有 {pending} 条告警待处置，请优先处理高等级事件。"
        advice = "建议登录告警中心完成处置，并回看关键截图。"
    else:
        risk = "今日告警均已处置，风险可控。"
        advice = "建议复盘高发区域与时段，优化禁区与灵敏度配置。"

    highlights_text = "\n".join(
        f"- [{item['created_at']}] {item['stream_label']} · "
        f"{item['type_label']}：{item['description'][:80]}"
        for item in stats.get("highlights", [])
    ) or "- 无重点事件"

    return f"""# 居家监控 AI 日报 — {report_date}

## 一、总体概览
- 告警总数：**{total}** 条（高等级 {high} 条）
- 处置情况：已处理 {handled} 条，待处理 {pending} 条
- 事件日志：**{stats['total_events']}** 条

## 二、告警分类
{_format_type_lines(stats.get('alerts_by_type', {}), ALERT_LABELS)}

## 三、事件分类
{_format_type_lines(stats.get('events_by_type', {}), EVENT_LABELS)}

## 四、摄像头分布
{_format_type_lines(stats.get('alerts_by_stream', {}), STREAM_LABELS)}

## 五、重点事件
{highlights_text}

## 六、AI 风险评估
{risk}

## 七、处置建议
{advice}
"""


def _build_ai_prompt(stats: dict[str, Any]) -> str:
    return (
        "你是居家智能摄像头系统的安防分析助手。请根据以下 JSON 统计数据，"
        "用专业、简洁的中文生成一份 Markdown 监控日报。"
        "结构包含：总体概览、告警分析、风险研判、处置建议。"
        "不要编造不存在的数据。\n\n"
        f"统计数据：\n{json.dumps(stats, ensure_ascii=False, indent=2)}"
    )


def _generate_ai_summary(stats: dict[str, Any]) -> str | None:
    """调用 OpenAI 兼容 Chat Completions API；未配置密钥时返回 None。"""
    api_key = os.getenv("DAILY_REPORT_AI_API_KEY", "").strip()
    if not api_key:
        return None

    base_url = os.getenv(
        "DAILY_REPORT_AI_BASE_URL", "https://api.openai.com/v1"
    ).rstrip("/")
    model = os.getenv("DAILY_REPORT_AI_MODEL", "gpt-4o-mini")
    timeout = float(os.getenv("DAILY_REPORT_AI_TIMEOUT", "30"))

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "你输出 Markdown 格式的中文安防监控日报，语气专业。",
            },
            {"role": "user", "content": _build_ai_prompt(stats)},
        ],
        "temperature": 0.4,
    }

    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        content = body["choices"][0]["message"]["content"]
        return str(content).strip()
    except (urllib.error.URLError, KeyError, IndexError, json.JSONDecodeError) as exc:
        logger.warning("AI 日报生成失败，将回退模板: %s", exc)
        return None


def generate_daily_report(household_id: int, report_date: date | None = None) -> DailyReport:
    """执行完整 AI 工作流并 upsert 日报记录。"""
    if report_date is None:
        report_date = timezone.localdate()

    stats = collect_daily_stats(household_id, report_date)
    summary = _generate_ai_summary(stats)
    source = "ai" if summary else "template"
    if not summary:
        summary = build_template_report(stats)

    title = f"监控日报 {report_date.isoformat()}"
    report, _created = DailyReport.objects.update_or_create(
        household_id=household_id,
        report_date=report_date,
        defaults={
            "title": title,
            "summary": summary,
            "stats": stats,
            "source": source,
        },
    )
    return report
