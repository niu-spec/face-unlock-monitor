# -*- coding: utf-8 -*-
"""生成居家摄像头场景项目任务分工表 PDF（总表）"""

import os
from datetime import date

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUT = os.path.join(ROOT, "docs", "项目管理", "项目任务分工表.pdf")
REPO_URL = "https://github.com/niu-spec/home-camera-monitor"
PROD_SERVER = "152.136.29.158"
PROD_PATH = "/service/home-camera-monitor"
FONT_PATH = r"C:\Windows\Fonts\msyh.ttc"
FONT_NAME = "MicrosoftYaHei"
DOCUMENT_DATE = date(2026, 7, 12)
ARCH_VERSION = "v1.6"

# A4 可用宽度（左右边距各 1.5cm）
PAGE_WIDTH = 18.0 * cm

TEAM = {
    "A": ("牛雨昊", "组长/前端/Git/部署/CI"),
    "B": ("苏哲勋", "流媒体/MediaMTX/视频拉流/云部署"),
    "C": ("王梓铭", "AI人脸/人员统计"),
    "D": ("李东礼", "AI危险区域/异常检测"),
    "E": ("刘帅华", "Django业务/数据库/Swagger/钉钉通知"),
    "F": ("刘澎潮", "专职文档"),
}

BRANCH_INFO = {
    "A": ("dev, feature/frontend, feature/infra", "frontend/ deploy/ .github/ Jenkinsfile"),
    "B": ("dev, feature/nginx", "apps/video_stream/ nginx/ deploy/"),
    "C": ("dev, feature/face", "apps/face/"),
    "D": ("dev, feature/detection", "apps/detection/"),
    "E": ("dev, feature/business", "apps/accounts/ households/ alerts/ zones/ events/ reports/"),
    "F": ("—（不写代码）", "docs/ + 飞书文档"),
}

STATUS_COLORS = {
    "完成": (colors.HexColor("#f0fff4"), colors.HexColor("#276749")),
    "待联调": (colors.HexColor("#fffaf0"), colors.HexColor("#c05621")),
    "进行中": (colors.HexColor("#ebf8ff"), colors.HexColor("#2b6cb0")),
}

# 第 5 列为状态：完成 / 待联调 / 进行中
TASKS = {
    "A": [
        ["1", "Vue3 工程初始化", "Element Plus + Router + Axios", "npm run dev 可访问", "完成", "P0"],
        ["2", "HomeMonitor.vue", "WebRTC iframe + FaceOverlay；活体标签", "可看实时画面+AI框", "完成", "P0"],
        ["3", "PersonStats.vue", "按摄像头展示 total/family/stranger", "切换流后数字正确", "完成", "P0"],
        ["4", "FamilyRegister.vue", "录入家人+角色+多帧活体", "注册成功", "完成", "P0"],
        ["5", "ZoneEditor.vue", "Canvas 画区域；forbidden_roles", "区域可保存", "完成", "P0"],
        ["6", "AlertCenter.vue", "告警列表；含音频/反欺骗类型筛选", "可处置告警", "完成", "P0"],
        ["7", "EventLog.vue", "事件时间线+截图回放", "EventReplayDialog 可回放", "完成", "P1"],
        ["8", "Login/Register + api", "JWT；Vite 代理 /api+/video_feed", "联调通过", "完成", "P0"],
        ["9", "HouseholdManage.vue", "家庭创建/切换/成员管理", "多家庭隔离", "完成", "P0"],
        ["10", "UserManage.vue", "用户管理页", "路由可达", "完成", "P1"],
        ["11", "DailyReport.vue", "AI 监控日报展示与生成", "模板/LLM 日报可用", "完成", "P1"],
        ["12", "FaceOverlay.vue", "WebRTC Canvas 叠加；轮询 presence", "/api/video/presence/ 200ms", "完成", "P0"],
        ["13", "危险区域联调修复", "stream 映射；presence 分路；坐标缩放", "禁区检测对齐", "完成", "P0"],
        ["14", "验收 bug 修复", "音频告警可见性；metadata；事件映射", "6640a0b 已合并 dev", "完成", "P0"],
        ["15", "deploy 脚本", "deploy-all.sh + start_backend", "B 组可一键部署", "完成", "P0"],
        ["16", "CI/CD", "Jenkinsfile + GitHub Actions", "CI 已通过；CD 待结题截图", "完成", "P0"],
        ["17", "Git 管理", "PR 审查；dev→main；Contributors", "中期/结题 tag", "进行中", "P0"],
    ],
    "B": [
        ["1", "云服务器+RTMP", f"Ubuntu {PROD_SERVER}；9090/8554/80", "推流成功", "完成", "P0"],
        ["2", "MediaMTX 部署", "Docker；RTMP :9090 / RTSP :8554", "OBS 可推流", "完成", "P0"],
        ["3", "WebRTC 预览", "MediaMTX :8889", "浏览器低延迟预览", "完成", "P0"],
        ["4", "video_stream 模块", "CameraWorker 采集/AI 分线程；process_frame", "worker 稳定运行", "完成", "P0"],
        ["5", "MJPEG 输出", "后端 /video_feed/ 含烧录标注", "调试/备用入口", "完成", "P0"],
        ["6", "多路流支持", "stream/1、stream/2 推流码", "前端可切换", "完成", "P0"],
        ["7", "生产 Nginx 反代", "80 → 8010；/api/ /video_feed/", "公网可访问", "完成", "P0"],
        ["8", "Jenkins 安装", "服务器 :8080 + Webhook", "Pipeline 可触发", "完成", "P0"],
        ["9", "Jenkins CD 配置", "Pipeline test/build/deploy；生产目录同步", "CD 流水线已配置", "完成", "P0"],
        ["10", "云部署联调", f"pull {PROD_PATH} 并重启 backend", "端到端 AI 演示已通过", "完成", "P0"],
    ],
    "C": [
        ["1", "dlib 环境+模型", "dat/ 两个模型文件", "import 成功", "完成", "P0"],
        ["2", "apps/face/services", "检测+128维编码+比对", "单元测试通过", "完成", "P0"],
        ["3", "家人注册 API", "POST /api/face/register/ 含 role", "Swagger 可测", "完成", "P0"],
        ["4", "实时识别", "WebRTC+Canvas 绿/红框；MJPEG 备用", "告警中心可见", "完成", "P0"],
        ["5", "人数统计", "分摄像头 presence 快照", "PersonStats 正确", "完成", "P0"],
        ["6", "presence API", "GET /api/video/presence/?stream_id=", "前端 200ms 轮询", "完成", "P0"],
        ["7", "陌生人告警", "未注册脸→FACE_UNKNOWN", "告警中心可见", "完成", "P0"],
        ["8", "face_encoding 持久化", "DB + JSON 备份", "重启数据仍在", "完成", "P0"],
        ["9", "活体反欺骗", "SPOOF/REPLAY/DEEPFAKE 检测", "liveness.py 已实现", "完成", "P0"],
        ["10", "多帧活体注册", "FaceLivenessView；注册≥3帧校验", "静态图无法注册", "完成", "P0"],
        ["11", "监控页活体状态", "/api/video/status 返回 liveness", "HomeMonitor 标签", "完成", "P1"],
        ["12", "presence/overlay 修复", "分路存储；streamId 映射", "e7930d6 已合并 dev", "完成", "P0"],
    ],
    "D": [
        ["1", "检测方案文档", "积水/着火/跌倒/禁区/音频算法", "docs/ 技术文档", "完成", "P0"],
        ["2", "行人检测", "YOLOv8n 优先 + HOG 降级", "可检出行人", "完成", "P0"],
        ["3", "区域闯入 INTRUSION", "child 进厨房多边形", "告警可触发", "完成", "P0"],
        ["4", "距边缘过近 PROXIMITY", "safe_distance 阈值", "告警可触发", "完成", "P0"],
        ["5", "异常停留 LOITER", "dwell_time 超时", "告警可触发", "完成", "P1"],
        ["6", "积水 WATER", "画面下部 HSV 蓝/反光", "模拟可告警", "完成", "P0"],
        ["7", "着火 FIRE", "高亮红/黄区域超阈值", "明火可告警", "完成", "P0"],
        ["8", "摔倒 FALL", "人体框高宽比异常", "躺倒可告警", "完成", "P0"],
        ["9", "区域坐标缩放", "ZoneEditor 640×480→检测帧", "坐标对齐修复", "完成", "P0"],
        ["10", "异常声学检测", "PANNs CNN14；SCREAM/FIGHT 等", "audio_service.py", "完成", "P0"],
        ["11", "音视频联动", "音频+视频→EMERGENCY", "av_correlation.py", "完成", "P0"],
        ["12", "音频状态 API", "GET /api/detection/audio/status/", "Swagger 可测", "完成", "P1"],
        ["13", "与 face 联动", "禁区需 role child/adult", "process_frame 链 E2E", "完成", "P0"],
    ],
    "E": [
        ["1", "Django settings + models", "MySQL；User/Household/Zone/Alert", "migrate 成功", "完成", "P0"],
        ["2", "households 多家庭", "家庭/成员/加入申请/摄像头", "数据隔离可用", "完成", "P0"],
        ["3", "zone 表", "forbidden_roles/points_json", "厨房禁区可配", "完成", "P0"],
        ["4", "auth/login", "JWT + 短信注册/登录", "A 可登录", "完成", "P0"],
        ["5", "zones CRUD", "GET/POST/PUT/DELETE", "A 画框可存", "完成", "P0"],
        ["6", "alert_service", "create_alert 供 C/D 调用", "统一写库+metadata", "完成", "P0"],
        ["7", "alerts API", "列表/处置/分页/筛选", "告警中心联调", "完成", "P0"],
        ["8", "events API", "识别/告警事件+快照回放", "EventLog 展示", "完成", "P0"],
        ["9", "reports API", "AI 监控日报生成", "DailyReport 可用", "完成", "P1"],
        ["10", "Swagger /api/docs", "drf-yasg 文档", "可访问", "完成", "P1"],
        ["11", "MySQL 生产部署", "云服务器建库", "生产可用", "完成", "P0"],
        ["12", "钉钉告警通知", "Webhook 推送+@主R", "NotificationSettings", "完成", "P0"],
        ["13", "告警升级链", "超时逐级上报+1领导", "checker 定时任务", "完成", "P1"],
    ],
    "F": [
        ["1", "文档模板+日报", "飞书 PRD + 组内日报", "7/6 起持续", "完成", "P0"],
        ["2", "v1.0 立项文档", "背景/需求/架构/分工", "7/8 提交", "完成", "P0"],
        ["3", "v2.0 中期文档", "概要设计/接口/库表", "7/11 提交", "完成", "P0"],
        ["4", "v3.0 结题文档", "测试/部署/总结", "7/15 提交", "进行中", "P0"],
        ["5", "演示视频", "注册→识人→禁区→异常→告警回放", "5-10min MP4", "进行中", "P0"],
        ["6", "维护 docs/", f"总体架构说明 {ARCH_VERSION}、README 索引", "与代码同步", "完成", "P1"],
        ["7", "任务分工表 PDF", "本 PDF（总表）", "7/12 更新", "完成", "P1"],
    ],
}

MILESTONES = [
    ["7/6—7/8", "立项", "Vue 骨架、MediaMTX、人脸 demo、Django models、v1.0 文档"],
    ["7/9—7/10", "集成", "Login/API、MJPEG、process_frame、YOLO 禁区、CI/CD、云部署"],
    ["7/11", "中期", "事件回放、AI 日报、Jenkins CD、活体反欺骗、声音识别、钉钉通知"],
    ["7/12—7/14", "联调", "WebRTC+overlay E2E、Camera 配置、Worker 线程安全、OpenSpec 归档"],
    ["7/15", "结题", "完整演示、v3.0 文档、main 发布"],
]

SCHEDULE = [
    ["7/6", "启动", "Vue init\nGit", "租服务器\nMediaMTX", "装dlib", "异常方案", "Django models", "文档模板"],
    ["7/7", "环境", "前端骨架", "RTMP通", "模型demo", "方案给F", "zone表", "v1.0草稿"],
    ["7/8", "立项", "监控页原型", "video_stream", "人脸demo", "—", "素材给F", "提交v1.0"],
    ["7/9", "联调", "Login+api", "MJPEG", "face/register", "—", "login+zones", "日报"],
    ["7/10", "集成", "WebRTC叠加\nCI/CD", "云部署\nNginx", "process_frame", "YOLO+禁区", "reports", "v1.4+PDF"],
    ["7/11", "中期", "事件回放\nAI日报\nbug修复", "Jenkins CD\n配置完成", "活体反欺骗\noverlay修复", "声音识别\nAV联动", "钉钉通知\n升级链", "v2.0+PDF"],
    ["7/12", "联调", "FaceOverlay\nE2E验收", "native-crash\n修复", "presence\n云上验收", "异常告警\n可见", "Camera\n绑定", "PDF\nv1.6"],
    ["7/13", "异常②", "EventLog\n部署", "生产8010", "—", "摔倒检测", "DB部署", "v3.0草稿"],
    ["7/14", "测试", "UI走查", "压测", "准确率", "告警测试", "Swagger", "视频"],
    ["7/15", "结题", "演示", "推流保障", "识人演示", "异常演示", "后端保障", "提交文档"],
]

SCHEDULE_COL = {"A": 2, "B": 3, "C": 4, "D": 5, "E": 6, "F": 7}

PERSON_APIS = {
    "A": [
        ["/api/households/", "CRUD", "家庭管理（联调）"],
        ["/api/events/", "GET", "事件记录展示"],
        ["/api/reports/daily/", "GET", "AI 监控日报"],
    ],
    "B": [
        ["/video_feed/{stream_id}", "GET", "MJPEG 备用（含烧录标注）"],
        ["/api/video/presence/", "GET", "overlay 框数据（主）"],
        ["/api/video/status", "GET", "worker 状态"],
        ["/api/video/streams/{id}/source", "GET", "RTSP/RTMP/WebRTC 地址"],
    ],
    "C": [
        ["/api/face/register/", "POST", "注册家人（含活体）"],
        ["/api/face/liveness/", "POST", "多帧活体检测"],
        ["/api/video/presence/", "GET", "人数+人脸框"],
    ],
    "D": [
        ["/api/detection/analyze/", "POST", "单帧异常/区域检测"],
        ["/api/detection/audio/status/", "GET", "音频检测状态"],
    ],
    "E": [
        ["/api/auth/login/", "POST", "JWT 登录"],
        ["/api/alerts/", "GET/POST", "告警列表"],
        ["/api/events/", "GET", "事件记录+回放"],
        ["/api/reports/daily/", "GET/POST", "AI 监控日报"],
        ["/api/notifications/config/", "GET/PUT", "钉钉通知配置"],
        ["/api/docs/", "GET", "Swagger 文档"],
    ],
    "F": [],
}

COLLAB_SCENES = {
    "A": [
        "FaceOverlay WebRTC Canvas 叠加 + 活体标签（与 B/C 协作）",
        "EventReplayDialog 事件回放 + DailyReport AI 日报",
        "OpenSpec ai-video-integration 已归档（2026-07-12）",
        "Jenkins + GitHub Actions CI（结题材料）",
    ],
    "B": [
        f"云服务器部署最新 dev（路径 {PROD_PATH}）",
        "CameraWorker 线程安全修复（fix/native-crash-thread-safety）",
        "Jenkins :8080 安装 + CD Pipeline 已配置",
    ],
    "C": [
        "process_frame 链集成；活体反欺骗与 presence 分路",
        "云上 WebRTC + overlay 端到端验收已完成（7/12）",
    ],
    "D": ["禁区+音频检测与 face role 联动；云上异常告警 E2E 已通过"],
    "E": ["钉钉通知需配置 Webhook；与 A 告警中心联调"],
}


def register_font():
    pdfmetrics.registerFont(TTFont(FONT_NAME, FONT_PATH, subfontIndex=0))
    return FONT_NAME


def build_styles(fn):
    return {
        "title": ParagraphStyle(
            "title", fontName=fn, fontSize=18, leading=24, alignment=TA_CENTER,
            spaceAfter=6, textColor=colors.HexColor("#1a365d"),
        ),
        "subtitle": ParagraphStyle(
            "subtitle", fontName=fn, fontSize=10, leading=15, alignment=TA_CENTER,
            spaceAfter=14, textColor=colors.HexColor("#4a5568"),
        ),
        "h1": ParagraphStyle(
            "h1", fontName=fn, fontSize=14, leading=20, spaceBefore=12, spaceAfter=8,
            textColor=colors.HexColor("#2c5282"),
        ),
        "h2": ParagraphStyle(
            "h2", fontName=fn, fontSize=11.5, leading=16, spaceBefore=10, spaceAfter=6,
            textColor=colors.HexColor("#2d3748"),
        ),
        "body": ParagraphStyle(
            "body", fontName=fn, fontSize=10, leading=15, spaceAfter=6, alignment=TA_LEFT,
        ),
        "small": ParagraphStyle(
            "small", fontName=fn, fontSize=9, leading=13,
            textColor=colors.HexColor("#4a5568"),
        ),
        "cell": ParagraphStyle(
            "cell", fontName=fn, fontSize=9, leading=13, alignment=TA_LEFT,
        ),
        "cell_bold": ParagraphStyle(
            "cell_bold", fontName=fn, fontSize=9.5, leading=14,
            textColor=colors.HexColor("#1a365d"), alignment=TA_LEFT,
        ),
        "cell_center": ParagraphStyle(
            "cell_center", fontName=fn, fontSize=9, leading=13, alignment=TA_CENTER,
        ),
        "code": ParagraphStyle(
            "code", fontName=fn, fontSize=9, leading=14, spaceAfter=4,
            textColor=colors.HexColor("#2d3748"), leftIndent=10,
        ),
    }


def _escape(text: str) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _task_detail_cell(detail: str, accept: str, prio: str, styles) -> Paragraph:
    prio_tag = f' <font color="#c53030">[{prio}]</font>' if prio == "P0" else ""
    html = (
        f"{_escape(detail)}<br/>"
        f'<font color="#718096">验收：{_escape(accept)}</font>{prio_tag}'
    )
    return Paragraph(html, styles["cell"])


def tbl(data, widths, styles, hdr=1, status_col=None):
    """通用表格；status_col 指定状态列索引以着色。"""
    rows = []
    for r, row in enumerate(data):
        nr = []
        for c, cell in enumerate(row):
            if r < hdr:
                st = styles["cell_bold"]
                txt = f"<b>{_escape(cell)}</b>"
            elif status_col is not None and c == status_col:
                st = styles["cell_center"]
                txt = f"<b>{_escape(cell)}</b>"
            else:
                st = styles["cell"]
                txt = _escape(cell).replace("\n", "<br/>")
            nr.append(Paragraph(txt, st))
        rows.append(nr)

    t = Table(rows, colWidths=widths, repeatRows=hdr)
    cmd = [
        ("BACKGROUND", (0, 0), (-1, hdr - 1), colors.HexColor("#ebf4ff")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    for i in range(hdr, len(data)):
        if i % 2 == 1:
            cmd.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f7fafc")))
        if status_col is not None:
            status = data[i][status_col]
            if status in STATUS_COLORS:
                bg, fg = STATUS_COLORS[status]
                cmd.append(("BACKGROUND", (status_col, i), (status_col, i), bg))
                cmd.append(("TEXTCOLOR", (status_col, i), (status_col, i), fg))
    t.setStyle(TableStyle(cmd))
    return t


def task_table(tasks, styles):
    """四列任务表：序号 | 任务项 | 说明与验收 | 状态"""
    header = ["序号", "任务项", "说明与验收标准", "状态"]
    rows = [[Paragraph(f"<b>{_escape(c)}</b>", styles["cell_bold"]) for c in header]]
    for no, name, detail, accept, status, prio in tasks:
        rows.append([
            Paragraph(_escape(no), styles["cell_center"]),
            Paragraph(f"<b>{_escape(name)}</b>", styles["cell"]),
            _task_detail_cell(detail, accept, prio, styles),
            Paragraph(f"<b>{_escape(status)}</b>", styles["cell_center"]),
        ])
    widths = [1.0 * cm, 3.8 * cm, 11.2 * cm, 2.0 * cm]
    t = Table(rows, colWidths=widths, repeatRows=1)
    cmd = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ebf4ff")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (3, 0), (3, -1), "CENTER"),
    ]
    for i, task in enumerate(tasks, start=1):
        if i % 2 == 1:
            cmd.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f7fafc")))
        status = task[4]
        if status in STATUS_COLORS:
            bg, fg = STATUS_COLORS[status]
            cmd.append(("BACKGROUND", (3, i), (3, i), bg))
            cmd.append(("TEXTCOLOR", (3, i), (3, i), fg))
    t.setStyle(TableStyle(cmd))
    return t


def person_section(story, styles, code, tasks, page_break=True):
    name, role = TEAM[code]
    if page_break:
        story.append(PageBreak())
    story.append(Paragraph(f"{code} — {name}", styles["h2"]))
    story.append(Paragraph(role, styles["small"]))
    story.append(Spacer(1, 6))
    story.append(task_table(tasks, styles))
    story.append(Spacer(1, 10))


def append_git_workflow(story, styles, code=None):
    story.append(Paragraph("Git 分支规范与协作流程", styles["h1"]))
    story.append(Paragraph(
        f"代码仓库：<b>{REPO_URL}</b><br/>"
        "各 feature 分支已合并至 <b>dev</b>；日常开发从 dev 拉取或提 PR 至 dev。",
        styles["body"],
    ))

    story.append(Paragraph("分支结构", styles["h2"]))
    story.append(tbl([
        ["分支", "用途", "谁可操作"],
        ["main", "稳定版，结题演示", "仅牛雨昊合并"],
        ["dev", "日常集成，联调基准", "PR 合并目标"],
        ["feature/*", "各人开发分支（已合入 dev）", "各成员 push"],
    ], [3.5 * cm, 6.5 * cm, 4.5 * cm], styles))

    story.append(Spacer(1, 6))
    story.append(Paragraph("分支对照表", styles["h2"]))
    branch_rows = [["成员", "Git 分支", "负责目录"]]
    for c, (name, _) in TEAM.items():
        branches, dirs = BRANCH_INFO[c]
        branch_rows.append([name, branches, dirs])
    story.append(tbl(branch_rows, [2.2 * cm, 5.5 * cm, 6.8 * cm], styles))

    if code and code != "F":
        branches, dirs = BRANCH_INFO[code]
        story.append(Spacer(1, 6))
        story.append(Paragraph("你的 Git 操作", styles["h2"]))
        story.append(Paragraph(
            f"<b>集成分支：</b>dev<br/>"
            f"<b>你的 feature 分支：</b>{branches}<br/>"
            f"<b>你的目录：</b>{dirs}",
            styles["body"],
        ))
    elif code == "F":
        story.append(Spacer(1, 6))
        story.append(Paragraph("文档协作说明", styles["h2"]))
        story.append(Paragraph(
            "你不参与 Git 代码分支。各成员每天 <b>17:00</b> 反馈文档素材；"
            f"你负责维护 <b>docs/</b> 目录（含总体架构说明 {ARCH_VERSION}）及飞书文档。",
            styles["body"],
        ))

    story.append(Spacer(1, 6))
    story.append(Paragraph("协作规范", styles["h2"]))
    story.append(Paragraph(
        "• 9:00 晨会（牛雨昊主持）<br/>"
        "• 17:00 各成员向刘澎潮反馈文档素材<br/>"
        "• 前端目录 frontend/ 仅牛雨昊修改<br/>"
        "• push 触发 GitHub Actions CI",
        styles["body"],
    ))


def append_overview_sections(story, styles):
    story.append(Paragraph("一、项目概述", styles["h1"]))
    story.append(Paragraph(
        "通过家庭摄像头实时监控家中画面：<b>人脸识别</b>、<b>人员统计</b>、"
        "<b>危险区域</b>、<b>异常检测</b>（积水、着火、摔倒、异常声音）。"
        "技术栈：Vue3 + Django + MediaMTX + OpenCV/dlib + MySQL。",
        styles["body"],
    ))

    story.append(Spacer(1, 6))
    story.append(Paragraph("1.0 当前进度摘要（7/12）", styles["h2"]))
    story.append(tbl([
        ["维度", "说明"],
        ["代码开发", "核心功能已全部完成（含 WebRTC overlay、活体反欺骗、声音识别、钉钉通知、事件回放、AI 日报）"],
        ["联调验收", "云上 OBS 推流 E2E 已通过：WebRTC 预览 + AI 标注 + 告警中心可见"],
        ["剩余工作", "演示视频 + v3.0 结题文档 + dev→main 发布 + Jenkins CD 结题截图"],
        ["CI 状态", "GitHub Actions CI 已通过；Jenkins CD 已配置"],
    ], [3.5 * cm, 12 * cm], styles))

    story.append(Spacer(1, 6))
    story.append(Paragraph(f"1.1 当前架构（{ARCH_VERSION}）", styles["h2"]))
    story.append(Paragraph(
        "<b>展示层</b>：Vue3 — WebRTC iframe 低延迟预览 + FaceOverlay Canvas（轮询 /api/video/presence/）<br/>"
        "<b>业务+AI 层</b>：Django 4.2 单体 — accounts / face / detection / video_stream / reports 等<br/>"
        "<b>流媒体</b>：OBS → RTMP(9090) → MediaMTX → RTSP → CameraWorker → process_frame()<br/>"
        "<b>MJPEG 备用</b>：/video_feed/{id} 后端烧录标注（调试入口）<br/>"
        f"<b>部署</b>：{PROD_SERVER}，Nginx :80 反代 :8010",
        styles["body"],
    ))

    story.append(Spacer(1, 6))
    story.append(Paragraph("1.2 功能与验收对应", styles["h2"]))
    story.append(tbl([
        ["验收模块", "分值", "实现情况", "状态"],
        ["人脸识别", "12+8", "注册+识别+陌生人+活体反欺骗", "已验收"],
        ["目标检测", "25", "危险区域+闯入/接近/逗留", "已验收"],
        ["实时视频检测", "20+8", "积水+着火+摔倒+异常声学", "已验收"],
        ["告警中心", "8+3+2", "展示+处置+回放+钉钉+AI日报", "已验收"],
        ["项目基础", "15", "GitHub/OpenSpec/Swagger/Jenkins", "基本完成"],
        ["文档", "10", "日报+设计文档+演示视频", "进行中"],
    ], [3.5 * cm, 1.5 * cm, 8.5 * cm, 2 * cm], styles))

    story.append(Spacer(1, 6))
    story.append(Paragraph("1.3 7/12 各组成果", styles["h2"]))
    story.append(tbl([
        ["组", "成员", "7/12 完成项"],
        ["A", "牛雨昊", "FaceOverlay E2E、ZoneEditor 检测叠加、OpenSpec 归档、文档同步"],
        ["B", "苏哲勋", "Worker 线程安全修复、Camera 配置、云部署联调"],
        ["C", "王梓铭", "WebRTC overlay 云上验收、活体反欺骗全流程"],
        ["D", "李东礼", "异常检测告警 E2E、禁区+face 联动验证"],
        ["E", "刘帅华", "Camera 绑定家庭、告警中心数据隔离"],
        ["F", "刘澎潮", "任务分工表 v1.6 更新、v3.0 文档筹备"],
    ], [1.2 * cm, 2.2 * cm, 12.1 * cm], styles))


def build_story(styles):
    s = []
    s.append(Paragraph("软件工程学期实训 II", styles["title"]))
    s.append(Paragraph("home-camera-monitor 项目任务分工表", styles["title"]))
    s.append(Paragraph(
        f"应用场景：居家智能摄像头监控<br/>"
        f"团队：牛雨昊、苏哲勋、王梓铭、李东礼、刘帅华、刘澎潮<br/>"
        f"{DOCUMENT_DATE.strftime('%Y-%m-%d')}（{ARCH_VERSION}）",
        styles["subtitle"],
    ))

    append_overview_sections(s, styles)
    s.append(PageBreak())

    s.append(Paragraph("二、团队分工总览", styles["h1"]))
    overview_rows = [["代号", "姓名", "角色", "Git 分支", "核心目录"]]
    for c, (name, role) in TEAM.items():
        branches, dirs = BRANCH_INFO[c]
        overview_rows.append([c, name, role, branches, dirs])
    s.append(tbl(overview_rows, [1.0 * cm, 1.8 * cm, 3.5 * cm, 4.2 * cm, 4.0 * cm], styles))

    s.append(PageBreak())
    append_git_workflow(s, styles)

    s.append(PageBreak())
    s.append(Paragraph("三、成员详细任务清单", styles["h1"]))
    s.append(Paragraph(
        "状态说明：<b>完成</b> = 已实现且云上 E2E 验收通过；"
        "<b>进行中</b> = 结题前待交付。",
        styles["small"],
    ))
    s.append(Spacer(1, 8))

    for i, code in enumerate(TEAM):
        person_section(s, styles, code, TASKS[code], page_break=(i > 0))

    s.append(PageBreak())
    s.append(Paragraph("四、关键 API 与告警类型", styles["h1"]))

    s.append(Paragraph("4.1 核心 API（节选）", styles["h2"]))
    s.append(tbl([
        ["接口", "负责人", "说明"],
        ["/video_feed/{id}", "苏哲勋", "MJPEG 备用（含烧录标注）"],
        ["/api/video/presence/", "苏哲勋/王梓铭", "overlay 框+人数（前端主数据源）"],
        ["/api/video/status", "苏哲勋", "worker 状态 + liveness"],
        ["/api/face/register/", "王梓铭", "家人注册（含多帧活体）"],
        ["/api/home/presence/", "王梓铭", "人数统计"],
        ["/api/detection/audio/status/", "李东礼", "音频检测状态"],
        ["/api/alerts/", "刘帅华", "告警列表与处置"],
        ["/api/events/", "刘帅华", "事件记录与回放"],
        ["/api/reports/daily/", "刘帅华", "AI 监控日报"],
        ["/api/notifications/config/", "刘帅华", "钉钉通知配置"],
    ], [5.5 * cm, 2.0 * cm, 8.0 * cm], styles))

    s.append(Spacer(1, 8))
    s.append(Paragraph("4.2 告警类型", styles["h2"]))
    s.append(tbl([
        ["类型", "含义", "负责人"],
        ["FACE_UNKNOWN", "陌生人", "王梓铭"],
        ["FACE_SPOOF/REPLAY/DEEPFAKE", "人脸欺骗攻击", "王梓铭"],
        ["INTRUSION/PROXIMITY/LOITER", "危险区域", "李东礼"],
        ["WATER/FIRE/FALL", "积水/着火/摔倒", "李东礼"],
        ["SCREAM/FIGHT/EMERGENCY", "异常声音/联动", "李东礼"],
    ], [4.5 * cm, 5.5 * cm, 2.5 * cm], styles))

    s.append(PageBreak())
    s.append(Paragraph("五、里程碑与结题演示", styles["h1"]))

    s.append(Paragraph("5.1 项目里程碑", styles["h2"]))
    s.append(tbl(
        [["阶段", "节点", "主要成果"]] + MILESTONES,
        [2.5 * cm, 1.5 * cm, 12.5 * cm], styles,
    ))

    s.append(Spacer(1, 10))
    s.append(Paragraph("5.2 结题演示流程", styles["h2"]))
    steps = [
        "登录并切换演示家庭 → 注册家人（多帧活体）",
        "OBS 推流 → 监控页 WebRTC 画面 + Canvas AI 标注",
        "显示人数统计 → 陌生人入镜 → FACE_UNKNOWN 告警",
        "小孩进厨房 → INTRUSION 告警",
        "模拟积水/着火/摔倒 → 对应告警",
        "告警中心处置 → 事件回放 → AI 日报",
        "（可选）音频联动 EMERGENCY → Jenkins Pipeline 演示",
    ]
    for i, step in enumerate(steps, 1):
        s.append(Paragraph(f"{i}. {step}", styles["body"]))

    s.append(Spacer(1, 12))
    s.append(Paragraph(REPO_URL, styles["subtitle"]))
    return s


def build_person_story(styles, code):
    name, role = TEAM[code]
    branches, dirs = BRANCH_INFO[code]
    s = []

    s.append(Paragraph("软件工程学期实训 II", styles["title"]))
    s.append(Paragraph(f"个人任务清单 — {name}", styles["title"]))
    s.append(Paragraph(
        f"代号 {code}　|　{role}<br/>"
        f"Git 分支：{branches}<br/>"
        f"负责目录：{dirs}<br/>"
        f"{DOCUMENT_DATE.strftime('%Y-%m-%d')}（{ARCH_VERSION}）",
        styles["subtitle"],
    ))

    s.append(PageBreak())
    s.append(Paragraph("一、你的任务清单", styles["h1"]))
    s.append(task_table(TASKS[code], styles))

    if PERSON_APIS.get(code):
        s.append(Spacer(1, 12))
        s.append(Paragraph("二、你负责的 API", styles["h1"]))
        api_rows = [["接口", "方法", "说明"]] + PERSON_APIS[code]
        s.append(tbl(api_rows, [5.5 * cm, 2.0 * cm, 8.0 * cm], styles))

    if COLLAB_SCENES.get(code):
        s.append(Spacer(1, 12))
        s.append(Paragraph("三、协作事项", styles["h1"]))
        for item in COLLAB_SCENES[code]:
            s.append(Paragraph(f"• {item}", styles["body"]))

    s.append(Spacer(1, 12))
    section_num = 4 if PERSON_APIS.get(code) or COLLAB_SCENES.get(code) else 2
    nums = ["", "一", "二", "三", "四"]
    s.append(Paragraph(f"{nums[section_num]}、你的按日进度", styles["h1"]))
    col = SCHEDULE_COL[code]
    schedule_rows = [["日期", "节点", "当日任务"]]
    for row in SCHEDULE:
        schedule_rows.append([row[0], row[1], row[col].replace("\n", "；")])
    s.append(tbl(schedule_rows, [2.0 * cm, 2.0 * cm, 12.5 * cm], styles))

    s.append(Spacer(1, 12))
    s.append(Paragraph("结题演示中与你相关的环节", styles["h2"]))
    demo_map = {
        "A": "监控主页、WebRTC 叠加、活体标签、告警中心、事件回放、AI 日报、CI 演示",
        "B": "MediaMTX 推流、WebRTC 预览、CameraWorker 稳定、云部署、Jenkins CD",
        "C": "家人注册（多帧活体）、实时识别、反欺骗告警、人数统计",
        "D": "厨房禁区、积水/着火/摔倒、异常声学+AV联动",
        "E": "登录鉴权、告警 CRUD、钉钉通知、Swagger、AI 日报 API",
        "F": "演示视频拍摄、结题 v3.0 文档、任务分工表维护",
    }
    s.append(Paragraph(demo_map[code], styles["body"]))
    s.append(Spacer(1, 12))
    s.append(Paragraph(REPO_URL, styles["subtitle"]))
    return s


def write_pdf(path, story):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    doc = SimpleDocTemplate(
        path,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )
    doc.build(story)


def main():
    fn = register_font()
    styles = build_styles(fn)

    write_pdf(OUTPUT, build_story(styles))
    print(f"总表 PDF 已生成: {OUTPUT}")


if __name__ == "__main__":
    main()
