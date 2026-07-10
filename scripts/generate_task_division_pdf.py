# -*- coding: utf-8 -*-
"""生成居家摄像头场景项目任务分工表 PDF（总表 + 各成员独立 PDF）"""

import os
from datetime import date

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUT = os.path.join(ROOT, "docs", "项目任务分工表.pdf")
MEMBER_OUTPUT_DIR = os.path.join(ROOT, "docs", "成员任务")
REPO_URL = "https://github.com/niu-spec/home-camera-monitor"
PROD_SERVER = "152.136.29.158"
PROD_PATH = "/service/home-camera-monitor"
FONT_PATH = r"C:\Windows\Fonts\msyh.ttc"
FONT_NAME = "MicrosoftYaHei"
DOCUMENT_DATE = date(2026, 7, 10)
ARCH_VERSION = "v1.4"

TEAM = {
    "A": ("牛雨昊", "组长/前端/Git/部署/CI"),
    "B": ("苏哲勋", "流媒体/MediaMTX/视频拉流/云部署"),
    "C": ("王梓铭", "AI人脸/人员统计"),
    "D": ("李东礼", "AI危险区域/异常检测"),
    "E": ("刘帅华", "Django业务/数据库/Swagger"),
    "F": ("刘澎潮", "专职文档"),
}

BRANCH_INFO = {
    "A": ("dev（集成）\nfeature/frontend\nfeature/infra", "frontend/ deploy/ .github/ Jenkinsfile"),
    "B": ("dev（集成）\nfeature/nginx", "apps/video_stream/ nginx/ deploy/"),
    "C": ("dev（集成）\nfeature/face", "apps/face/"),
    "D": ("dev（集成）\nfeature/detection", "apps/detection/"),
    "E": ("dev（集成）\nfeature/business", "apps/accounts/ households/ alerts/ zones/ events/ reports/"),
    "F": ("—（不写代码）", "docs/ + 飞书文档"),
}

# 第 5 列为状态：完成 / 待云验收 / 进行中
TASKS = {
    "A": [
        ["1", "Vue3 工程初始化", "Element Plus + Router + Axios", "npm run dev 可访问", "完成", "P0"],
        ["2", "HomeMonitor.vue", "多路 MJPEG/WebRTC；嵌入 PersonStats", "可看实时画面", "完成", "P0"],
        ["3", "PersonStats.vue", "展示 total/family/stranger", "数字随识别更新", "待云验收", "P0"],
        ["4", "FamilyRegister.vue", "录入家人+角色+拍照", "注册成功", "完成", "P0"],
        ["5", "ZoneEditor.vue", "Canvas 画区域；设 forbidden_roles", "区域可保存", "完成", "P0"],
        ["6", "AlertCenter.vue", "告警列表；按类型筛选/处置", "可处置告警", "完成", "P0"],
        ["7", "EventLog.vue", "事件时间线+截图回放", "可查历史", "完成", "P1"],
        ["8", "Login/Register + api", "JWT；Vite 代理 /api+/video_feed", "联调通过", "完成", "P0"],
        ["9", "HouseholdManage.vue", "家庭创建/切换/成员管理", "多家庭隔离", "完成", "P0"],
        ["10", "UserManage.vue", "用户管理页", "路由可达", "完成", "P1"],
        ["11", "DailyReport.vue", "AI 监控日报展示", "可查看日报", "完成", "P1"],
        ["12", "FaceOverlay.vue", "WebRTC Canvas 叠加 AI 框", "轮询 /api/video/status", "待云验收", "P0"],
        ["13", "deploy 脚本", "deploy-all.sh + start_backend", "B 组可一键部署", "完成", "P0"],
        ["14", "CI/CD", "Jenkinsfile + GitHub Actions", "CI 已通过", "完成", "P0"],
        ["15", "Git 管理", "PR 审查；dev→main；Contributors", "中期/结题 tag", "进行中", "P0"],
    ],
    "B": [
        ["1", "云服务器+RTMP", f"Ubuntu {PROD_SERVER}；9090/8554/80", "推流成功", "完成", "P0"],
        ["2", "MediaMTX 部署", "Docker；RTMP :9090 / RTSP :8554", "OBS 可推流", "完成", "P0"],
        ["3", "WebRTC 预览", "MediaMTX :8889", "浏览器低延迟预览", "完成", "P0"],
        ["4", "video_stream 模块", "OpenCV 拉 RTSP；process_frame 链", "worker 可启动", "完成", "P0"],
        ["5", "MJPEG 输出", "StreamingHttpResponse", "/video_feed/{id} 可看", "完成", "P0"],
        ["6", "多路流支持", "stream/1、stream/2 推流码", "前端可切换", "完成", "P0"],
        ["7", "生产 Nginx 反代", "80 → 8010；/api/ /video_feed/", "公网可访问", "完成", "P0"],
        ["8", "云部署最新 dev", f"pull {PROD_PATH} 并重启 backend", "端到端 AI 联调", "待云验收", "P0"],
        ["9", "Jenkins 安装", "服务器 :8080 + Webhook", "Pipeline 可触发", "进行中", "P1"],
    ],
    "C": [
        ["1", "dlib 环境+模型", "dat/ 两个模型文件", "import 成功", "完成", "P0"],
        ["2", "apps/face/services", "检测+128维编码+比对", "单元测试通过", "完成", "P0"],
        ["3", "家人注册 API", "POST /api/face/register/ 含 role", "Swagger 可测", "完成", "P0"],
        ["4", "实时识别", "MJPEG 绿框家人/红框陌生人", "标注正确", "待云验收", "P0"],
        ["5", "人数统计", "total/family/stranger 快照", "presence API 可读", "待云验收", "P0"],
        ["6", "home/presence API", "GET /api/home/presence/", "前端可轮询", "待云验收", "P0"],
        ["7", "陌生人告警", "未注册脸→FACE_UNKNOWN", "告警中心可见", "完成", "P0"],
        ["8", "face_encoding 持久化", "DB + JSON 备份", "重启数据仍在", "完成", "P0"],
    ],
    "D": [
        ["1", "检测方案文档", "积水/着火/跌倒/禁区算法", "docs/ 技术文档", "完成", "P0"],
        ["2", "行人检测", "YOLOv8n 优先 + HOG 降级", "可检出行人", "完成", "P0"],
        ["3", "区域闯入 INTRUSION", "child 进厨房多边形", "告警可触发", "完成", "P0"],
        ["4", "距边缘过近 PROXIMITY", "safe_distance 阈值", "告警可触发", "完成", "P0"],
        ["5", "异常停留 LOITER", "dwell_time 超时", "告警可触发", "完成", "P1"],
        ["6", "积水 WATER", "画面下部 HSV 蓝/反光", "模拟可告警", "完成", "P0"],
        ["7", "着火 FIRE", "高亮红/黄区域超阈值", "明火可告警", "完成", "P0"],
        ["8", "摔倒 FALL", "人体框高宽比异常", "躺倒可告警", "完成", "P0"],
        ["9", "与 face 联动", "禁区需 role child/adult", "process_frame 链", "待云验收", "P0"],
    ],
    "E": [
        ["1", "Django settings + models", "MySQL；User/Household/Zone/Alert", "migrate 成功", "完成", "P0"],
        ["2", "households 多家庭", "家庭/成员/加入申请/摄像头", "数据隔离可用", "完成", "P0"],
        ["3", "zone 表", "forbidden_roles/points_json", "厨房禁区可配", "完成", "P0"],
        ["4", "auth/login", "JWT + 短信注册/登录", "A 可登录", "完成", "P0"],
        ["5", "zones CRUD", "GET/POST/PUT/DELETE", "A 画框可存", "完成", "P0"],
        ["6", "alert_service", "create_alert 供 C/D 调用", "统一写库", "完成", "P0"],
        ["7", "alerts API", "列表/处置/分页/筛选", "告警中心联调", "完成", "P0"],
        ["8", "events API", "识别/告警事件+快照", "EventLog 展示", "完成", "P0"],
        ["9", "reports API", "AI 监控日报", "DailyReport 可用", "完成", "P1"],
        ["10", "Swagger /api/docs", "drf-yasg 文档", "可访问", "完成", "P1"],
        ["11", "MySQL 生产部署", "云服务器建库", "生产可用", "完成", "P0"],
    ],
    "F": [
        ["1", "文档模板+日报", "飞书 PRD + 组内日报", "7/6 起持续", "完成", "P0"],
        ["2", "v1.0 立项文档", "背景/需求/架构/分工", "7/8 提交", "完成", "P0"],
        ["3", "v2.0 中期文档", "概要设计/接口/库表", "7/11 提交", "完成", "P0"],
        ["4", "v3.0 结题文档", "测试/部署/总结", "7/15 提交", "进行中", "P0"],
        ["5", "演示视频", "注册→识人→数人→禁区→异常", "5-10min MP4", "进行中", "P0"],
        ["6", "维护 docs/", "总体架构说明 v1.4、README 索引", "与代码同步", "完成", "P1"],
        ["7", "任务分工表 PDF", "本 PDF + 成员任务清单", "7/10 更新", "完成", "P1"],
    ],
}

SCHEDULE = [
    ["7/6", "启动", "Vue init\nGit", "租服务器\nMediaMTX", "装dlib", "异常方案", "Django models", "文档模板"],
    ["7/7", "环境", "前端骨架", "RTMP通", "模型demo", "方案给F", "zone表", "v1.0草稿"],
    ["7/8", "立项", "监控页原型", "video_stream", "人脸demo", "—", "素材给F", "提交v1.0"],
    ["7/9", "联调", "Login+api", "MJPEG", "face/register", "—", "login+zones", "日报"],
    ["7/10", "集成", "WebRTC叠加\nCI/CD", "云部署\nNginx", "process_frame", "YOLO+禁区", "reports", "v1.4+PDF"],
    ["7/11", "中期", "HomeMonitor\nPersonStats", "联调", "presence API", "PROXIMITY", "Swagger", "v2.0"],
    ["7/12", "异常①", "AlertCenter", "WebRTC", "—", "积水+着火", "告警CRUD", "日报"],
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
        ["/video_feed/{stream_id}", "GET", "MJPEG 实时画面"],
        ["/api/video/status", "GET", "worker 状态+AI 框数据"],
        ["/api/video/streams/{id}/source", "GET", "RTSP/RTMP/WebRTC 地址"],
    ],
    "C": [
        ["/api/face/register/", "POST", "{name,role,image}"],
        ["/api/face/analyze/", "POST", "单帧人脸分析"],
        ["/api/home/presence/", "GET", "{total,family,stranger}"],
    ],
    "D": [
        ["/api/detection/analyze/", "POST", "单帧异常/区域检测"],
        ["/api/detection/status/", "GET", "检测模块状态"],
    ],
    "E": [
        ["/api/auth/login/", "POST", "JWT 登录"],
        ["/api/households/", "CRUD", "家庭管理与多租户"],
        ["/api/zones/", "CRUD", "含 forbidden_roles"],
        ["/api/alerts/", "GET/POST", "告警列表/内部写入"],
        ["/api/alerts/{id}/handle/", "PUT", "告警处置"],
        ["/api/events/", "GET", "事件记录"],
        ["/api/reports/daily/", "GET/POST", "AI 监控日报"],
        ["/api/docs/", "GET", "Swagger（drf-yasg）"],
    ],
    "F": [],
}

COLLAB_SCENES = {
    "A": [
        "PersonStats 展示人数（与王梓铭协作）",
        "FaceOverlay WebRTC 叠加（与苏哲勋 /video/status 协作）",
        "Jenkins + GitHub Actions CI（结题材料）",
    ],
    "B": [
        "云服务器部署最新 dev（路径 {0}）".format(PROD_PATH),
        "Jenkins :8080 安装（见 docs/B组-Jenkins安装指引.md）",
    ],
    "C": ["process_frame 链集成；云上 presence 端到端验收（与 B 协作）"],
    "D": ["禁区检测需 face 模块提供 role；云上告警端到端验收"],
}


def register_font():
    pdfmetrics.registerFont(TTFont(FONT_NAME, FONT_PATH, subfontIndex=0))
    return FONT_NAME


def build_styles(fn):
    return {
        "title": ParagraphStyle("title", fontName=fn, fontSize=17, leading=22, alignment=TA_CENTER,
                                spaceAfter=8, textColor=colors.HexColor("#1a365d")),
        "subtitle": ParagraphStyle("subtitle", fontName=fn, fontSize=9.5, leading=14, alignment=TA_CENTER,
                                   spaceAfter=12, textColor=colors.HexColor("#4a5568")),
        "h1": ParagraphStyle("h1", fontName=fn, fontSize=13, leading=18, spaceBefore=10, spaceAfter=5,
                             textColor=colors.HexColor("#2c5282")),
        "h2": ParagraphStyle("h2", fontName=fn, fontSize=10.5, leading=15, spaceBefore=7, spaceAfter=4,
                             textColor=colors.HexColor("#2d3748")),
        "body": ParagraphStyle("body", fontName=fn, fontSize=9, leading=13, spaceAfter=5),
        "small": ParagraphStyle("small", fontName=fn, fontSize=8, leading=11, textColor=colors.HexColor("#4a5568")),
        "cell": ParagraphStyle("cell", fontName=fn, fontSize=6.8, leading=10),
        "cell_bold": ParagraphStyle("cell_bold", fontName=fn, fontSize=6.8, leading=10,
                                    textColor=colors.HexColor("#1a365d")),
        "code": ParagraphStyle("code", fontName=fn, fontSize=8, leading=12, spaceAfter=4,
                               textColor=colors.HexColor("#2d3748"), leftIndent=8),
    }


def tbl(data, widths, styles, hdr=1):
    rows = []
    for r, row in enumerate(data):
        nr = []
        for cell in row:
            st = styles["cell_bold"] if r < hdr else styles["cell"]
            txt = f"<b>{cell}</b>" if r < hdr else cell.replace("<", "&lt;").replace(">", "&gt;")
            nr.append(Paragraph(txt.replace("\n", "<br/>"), st))
        rows.append(nr)
    t = Table(rows, colWidths=widths, repeatRows=hdr)
    cmd = [
        ("BACKGROUND", (0, 0), (-1, hdr - 1), colors.HexColor("#ebf4ff")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]
    for i in range(hdr, len(data)):
        if i % 2 == 0:
            cmd.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f7fafc")))
    t.setStyle(TableStyle(cmd))
    return t


def person_section(story, styles, code, tasks):
    name, role = TEAM[code]
    story.append(Paragraph(f"{code} — {name}（{role}）", styles["h2"]))
    header = ["序号", "任务项", "详细说明", "交付物/验收标准", "状态", "优先级"]
    story.append(tbl([header] + tasks,
                     [0.6 * cm, 3.2 * cm, 4.5 * cm, 2.8 * cm, 1.2 * cm, 0.9 * cm], styles))
    story.append(Spacer(1, 5))


def append_git_workflow(story, styles, code=None):
    story.append(Paragraph("Git 分支规范与协作流程", styles["h1"]))
    story.append(Paragraph(
        f"代码仓库：<b>{REPO_URL}</b><br/>"
        "各 feature 分支已合并至 <b>dev</b>（当前集成主线）；日常开发从 dev 拉取或提 PR 至 dev。",
        styles["body"],
    ))

    story.append(Paragraph("分支结构", styles["h2"]))
    story.append(tbl([
        ["分支", "用途", "谁可操作"],
        ["main", "稳定版，结题演示", "仅牛雨昊合并"],
        ["dev", "日常集成，联调基准", "PR 合并目标"],
        ["feature/*", "各人开发分支（已合入 dev）", "各成员 push"],
    ], [3 * cm, 5 * cm, 5.5 * cm], styles))

    story.append(Paragraph("分支对照表", styles["h2"]))
    branch_rows = [["成员", "Git 分支", "负责目录"]]
    for c, (name, _) in TEAM.items():
        branches, dirs = BRANCH_INFO[c]
        branch_rows.append([name, branches, dirs])
    story.append(tbl(branch_rows, [2.5 * cm, 4.5 * cm, 6.5 * cm], styles))

    if code and code != "F":
        branches, dirs = BRANCH_INFO[code]
        primary = "dev" if "dev" in branches else branches.split("\n")[0]
        story.append(Paragraph("你的 Git 操作", styles["h2"]))
        story.append(Paragraph(
            f"<b>集成分支：</b>dev<br/>"
            f"<b>你的 feature 分支：</b>{branches.replace(chr(10), '、')}<br/>"
            f"<b>你的目录：</b>{dirs}",
            styles["body"],
        ))
        story.append(Paragraph("首次拉代码", styles["h2"]))
        story.append(Paragraph(
            f"git clone {REPO_URL}.git<br/>"
            f"cd home-camera-monitor<br/>"
            f"git checkout dev",
            styles["code"],
        ))
        story.append(Paragraph("日常开发", styles["h2"]))
        story.append(Paragraph(
            "1. 同步：git pull origin dev<br/>"
            f"2. 开发提交：git add . → git commit -m \"feat(模块): 简述\" → git push origin dev<br/>"
            "3. 或 feature 分支 → PR 至 dev，Assign 牛雨昊 Review<br/>"
            "4. push 后 GitHub Actions 自动跑 CI",
            styles["body"],
        ))
    elif code == "F":
        story.append(Paragraph("文档协作说明", styles["h2"]))
        story.append(Paragraph(
            "你不参与 Git 代码分支。各成员每天 <b>17:00</b> 反馈文档素材；"
            f"你负责维护 <b>docs/</b> 目录（含总体架构说明 {ARCH_VERSION}）及飞书文档。",
            styles["body"],
        ))
    else:
        story.append(Paragraph("首次拉代码（通用）", styles["h2"]))
        story.append(Paragraph(
            f"git clone {REPO_URL}.git<br/>"
            "cd home-camera-monitor<br/>"
            "git checkout dev",
            styles["code"],
        ))
        story.append(Paragraph("开发流程", styles["h2"]))
        story.append(Paragraph(
            "feature/* → PR → dev →（结题 7/15）→ main<br/>"
            "• 禁止直接 push 到 main<br/>"
            "• Commit 使用真实姓名（课程统计 Contributors）<br/>"
            "• 不要修改他人负责目录<br/>"
            "• PR 合并方式：Squash and merge<br/>"
            "• push 触发 GitHub Actions CI（backend-test + frontend-build）",
            styles["body"],
        ))

    story.append(Paragraph("协作规范", styles["h2"]))
    story.append(Paragraph(
        "• 9:00 晨会（牛雨昊主持）<br/>"
        "• 17:00 各成员向刘澎潮反馈文档素材<br/>"
        "• 前端目录 frontend/ 仅牛雨昊修改<br/>"
        "• 结题（7/15）由牛雨昊打 tag 并合并 main",
        styles["body"],
    ))
    story.append(Spacer(1, 6))


def append_overview_sections(story, styles):
    story.append(Paragraph("一、项目概述", styles["h1"]))
    story.append(Paragraph(
        "通过家庭摄像头实时监控家中画面：<b>人脸识别</b>（识别家人/陌生人）、"
        "<b>人员统计</b>（当前在家人数）、<b>危险区域</b>（如厨房禁止小孩进入）、"
        "<b>异常检测</b>（积水、着火、摔倒）。"
        "技术栈：Vue3 + Django + MediaMTX + OpenCV/dlib + MySQL。",
        styles["body"],
    ))

    story.append(Paragraph(f"1.0 当前架构（{ARCH_VERSION}）", styles["h2"]))
    story.append(Paragraph(
        "<b>展示层</b>：Vue3 前端（5173）→ REST API + MJPEG / WebRTC<br/>"
        "<b>业务+AI 层</b>：Django 4.2 单体（8000 本地 / <b>8010 生产</b>）— "
        "accounts / households / zones / alerts / events / face / detection / video_stream / reports<br/>"
        "<b>流媒体</b>：OBS/摄像头 → RTMP(9090) → MediaMTX → RTSP(8554) / WebRTC(8889) → "
        "Django OpenCV → /video_feed/{id}<br/>"
        f"<b>部署</b>：{PROD_SERVER}，路径 {PROD_PATH}，Nginx :80 反代<br/>"
        "<b>数据层</b>：MySQL（多家庭数据隔离）",
        styles["body"],
    ))

    story.append(Paragraph("1.1 CI/CD（2026-07-10）", styles["h2"]))
    story.append(tbl([
        ["方案", "位置", "说明", "状态"],
        ["GitHub Actions", "GitHub 仓库", "push/PR 自动 backend-test + frontend-build", "✅ 已通过"],
        ["Jenkins", f"{PROD_SERVER}:8080", "Pipeline test/build/deploy（结题材料）", "⏳ 待 B 组安装"],
        ["GitLab CI", "—", "已弃用（组员无法注册）", "—"],
    ], [2.5 * cm, 3 * cm, 5.5 * cm, 1.5 * cm], styles))

    story.append(Paragraph("1.2 功能与验收对应", styles["h2"]))
    story.append(tbl([
        ["验收模块", "分值", "居家场景实现", "状态"],
        ["人脸识别", "12", "家人注册+识别+陌生人告警+存储", "代码完成"],
        ["目标检测", "25", "危险区域+厨房禁小孩+闯入/接近/逗留", "代码完成"],
        ["实时视频检测", "20", "积水+着火+摔倒（3种异常）", "代码完成"],
        ["告警中心", "8", "展示+处置+日志+回放", "代码完成"],
        ["项目基础", "3", "GitHub 分支/Network/Contributors", "进行中"],
        ["文档", "10", "日报+设计文档+演示视频", "进行中"],
    ], [2.2 * cm, 0.8 * cm, 7.5 * cm, 1.8 * cm], styles))
    story.append(Spacer(1, 6))

    story.append(Paragraph("1.3 核心业务场景", styles["h2"]))
    story.append(tbl([
        ["场景", "告警类型", "负责人"],
        ["识别家人", "—（绿框显示姓名）", "王梓铭"],
        ["陌生人出现", "FACE_UNKNOWN", "王梓铭"],
        ["统计当前人数", "前端 PersonStats 展示", "王梓铭+牛雨昊"],
        ["小孩进入厨房", "INTRUSION", "李东礼"],
        ["距边缘过近", "PROXIMITY", "李东礼"],
        ["异常停留", "LOITER", "李东礼"],
        ["地面积水", "WATER", "李东礼"],
        ["着火/明火", "FIRE", "李东礼"],
        ["人员摔倒", "FALL", "李东礼"],
    ], [3.2 * cm, 3.2 * cm, 3.1 * cm], styles))

    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "<b>待云验收（OpenSpec 4.1/4.2）</b>：云上部署最新 dev 后，"
        "MJPEG/WebRTC 实时 AI 画框 + presence 人数 + 告警端到端演示。",
        styles["small"],
    ))


def build_story(styles):
    s = []
    s.append(Paragraph("软件工程学期实训 II", styles["title"]))
    s.append(Paragraph("home-camera-monitor 项目任务分工表", styles["title"]))
    s.append(Paragraph(
        f"应用场景：<b>居家智能摄像头监控</b>　|　{REPO_URL}<br/>"
        f"团队：牛雨昊、苏哲勋、王梓铭、李东礼、刘帅华、刘澎潮　|　"
        f"{DOCUMENT_DATE}（{ARCH_VERSION}）",
        styles["subtitle"],
    ))

    append_overview_sections(s, styles)
    s.append(PageBreak())

    s.append(Paragraph("二、团队分工总览", styles["h1"]))
    overview_rows = [["代号", "姓名", "角色", "Git 分支", "核心目录"]]
    for c, (name, role) in TEAM.items():
        branches, dirs = BRANCH_INFO[c]
        overview_rows.append([c, name, role, branches, dirs])
    s.append(tbl(overview_rows, [0.7 * cm, 1.2 * cm, 2.5 * cm, 2.5 * cm, 4.6 * cm], styles))

    s.append(PageBreak())
    append_git_workflow(s, styles)

    s.append(PageBreak())
    s.append(Paragraph("三、成员详细任务清单", styles["h1"]))
    s.append(Paragraph(
        "状态说明：<b>完成</b>=代码/本地验收通过；"
        "<b>待云验收</b>=需 B 组部署最新 dev 后端到端验证；"
        "<b>进行中</b>=结题前待交付。",
        styles["small"],
    ))
    s.append(Spacer(1, 4))
    for code in TEAM:
        person_section(s, styles, code, TASKS[code])
        if code == "C":
            s.append(PageBreak())

    s.append(PageBreak())
    s.append(Paragraph("四、API 接口清单", styles["h1"]))
    s.append(tbl([
        ["接口", "方法", "负责人", "说明"],
        ["/video_feed/{stream_id}", "GET", "苏哲勋", "MJPEG 实时画面（含 AI 画框）"],
        ["/api/video/status", "GET", "苏哲勋", "worker 状态 + 人脸框数据"],
        ["/api/video/streams/{id}/source", "GET", "苏哲勋", "RTSP/RTMP/WebRTC 地址"],
        ["/api/face/register/", "POST", "王梓铭", "{name,role,image}"],
        ["/api/home/presence/", "GET", "王梓铭", "{total,family,stranger}"],
        ["/api/detection/analyze/", "POST", "李东礼", "单帧区域/异常检测"],
        ["/api/auth/login/", "POST", "刘帅华", "JWT 登录"],
        ["/api/households/", "CRUD", "刘帅华", "家庭管理与多租户"],
        ["/api/zones/", "CRUD", "刘帅华", "含 forbidden_roles"],
        ["/api/alerts/", "GET/POST", "刘帅华", "告警列表/内部写入"],
        ["/api/alerts/{id}/handle/", "PUT", "刘帅华", "告警处置"],
        ["/api/events/", "GET", "刘帅华", "事件记录+快照"],
        ["/api/reports/daily/", "GET/POST", "刘帅华", "AI 监控日报"],
        ["/api/snapshots/{filename}/", "GET", "刘帅华", "事件回放截图"],
        ["/api/docs/", "GET", "刘帅华", "Swagger（drf-yasg）"],
    ], [3 * cm, 1.2 * cm, 1.3 * cm, 6 * cm], styles))

    s.append(Paragraph("4.1 告警类型", styles["h2"]))
    s.append(tbl([
        ["type", "含义", "检测模块", "负责人"],
        ["FACE_UNKNOWN", "陌生人", "apps/face", "王梓铭"],
        ["INTRUSION", "危险区域闯入", "apps/detection+face", "李东礼"],
        ["PROXIMITY", "距离过近", "apps/detection", "李东礼"],
        ["LOITER", "异常停留", "apps/detection", "李东礼"],
        ["WATER", "积水", "apps/detection", "李东礼"],
        ["FIRE", "着火", "apps/detection", "李东礼"],
        ["FALL", "摔倒", "apps/detection", "李东礼"],
    ], [2.2 * cm, 2 * cm, 3.2 * cm, 1.5 * cm], styles))

    s.append(PageBreak())
    s.append(Paragraph("五、按日进度（7/6 — 7/15）", styles["h1"]))
    s.append(Paragraph(
        "下表为立项计划；<b>7/10 实际进度</b>见第三节任务清单「状态」列。",
        styles["small"],
    ))
    s.append(Spacer(1, 4))
    s.append(tbl(
        [["日期", "节点", "牛雨昊", "苏哲勋", "王梓铭", "李东礼", "刘帅华", "刘澎潮"]] + SCHEDULE,
        [0.85 * cm, 0.85 * cm, 1.8 * cm, 1.8 * cm, 1.8 * cm, 1.8 * cm, 1.8 * cm, 1.8 * cm],
        styles,
    ))

    s.append(Spacer(1, 6))
    s.append(Paragraph("5.1 结题演示流程", styles["h2"]))
    s.append(Paragraph(
        "1. 登录并切换演示家庭 → 注册爸爸/妈妈/小孩 → "
        "2. OBS 推流至客厅 → 监控页 MJPEG/WebRTC 实时画面 → "
        "3. 显示人数统计（家人/陌生人）→ "
        "4. 陌生人入镜 → FACE_UNKNOWN 告警 → "
        "5. 小孩进厨房 → INTRUSION 告警 → "
        "6. 模拟积水/着火/摔倒 → 对应告警 → "
        "7. 告警中心处置 + 事件回放 → "
        "8. （可选）Jenkins Pipeline 构建演示",
        styles["body"],
    ))
    s.append(Spacer(1, 8))
    s.append(Paragraph(REPO_URL, styles["subtitle"]))
    return s


def build_person_story(styles, code):
    name, role = TEAM[code]
    branches, dirs = BRANCH_INFO[code]
    s = []

    s.append(Paragraph("软件工程学期实训 II", styles["title"]))
    s.append(Paragraph(f"个人任务清单 — {name}", styles["title"]))
    s.append(Paragraph(
        f"代号 {code}　|　{role}　|　{REPO_URL}<br/>"
        f"Git：{branches.replace(chr(10), '、')}　|　目录：{dirs}　|　"
        f"{DOCUMENT_DATE}（{ARCH_VERSION}）",
        styles["subtitle"],
    ))

    append_git_workflow(s, styles, code=code)
    s.append(PageBreak())

    s.append(Paragraph("一、你的任务清单", styles["h1"]))
    header = ["序号", "任务项", "详细说明", "交付物/验收标准", "状态", "优先级"]
    s.append(tbl([header] + TASKS[code],
                 [0.6 * cm, 3.0 * cm, 4.3 * cm, 3.0 * cm, 1.2 * cm, 0.9 * cm], styles))

    if PERSON_APIS.get(code):
        s.append(Spacer(1, 8))
        s.append(Paragraph("二、你负责的 API", styles["h1"]))
        api_rows = [["接口", "方法", "说明"]] + PERSON_APIS[code]
        s.append(tbl(api_rows, [4 * cm, 1.5 * cm, 8 * cm], styles))

    if COLLAB_SCENES.get(code):
        s.append(Spacer(1, 8))
        s.append(Paragraph("三、协作事项", styles["h1"]))
        for item in COLLAB_SCENES[code]:
            s.append(Paragraph(f"• {item}", styles["body"]))

    s.append(Spacer(1, 8))
    section_num = 4 if PERSON_APIS.get(code) or COLLAB_SCENES.get(code) else 2
    s.append(Paragraph(f"{['', '一', '二', '三', '四'][section_num]}、你的按日进度", styles["h1"]))
    col = SCHEDULE_COL[code]
    schedule_rows = [["日期", "节点", "当日任务"]]
    for row in SCHEDULE:
        schedule_rows.append([row[0], row[1], row[col]])
    s.append(tbl(schedule_rows, [2 * cm, 2 * cm, 10.5 * cm], styles))

    s.append(Spacer(1, 8))
    s.append(Paragraph("结题演示中与你相关的环节", styles["h2"]))
    demo_map = {
        "A": "监控主页、WebRTC 叠加、家庭/用户管理、人数面板、告警中心、事件回放、CI 演示",
        "B": "MediaMTX 推流、MJPEG/WebRTC 预览、云部署、Jenkins",
        "C": "家人注册、实时识别、陌生人告警、人数统计（presence）",
        "D": "厨房禁区闯入、接近/逗留、积水/着火/摔倒异常检测",
        "E": "登录鉴权、家庭/区域/告警 CRUD、Swagger、AI 日报 API",
        "F": "演示视频拍摄、结题 v3.0 文档、任务分工表维护",
    }
    s.append(Paragraph(demo_map[code], styles["body"]))
    s.append(Spacer(1, 8))
    s.append(Paragraph(REPO_URL, styles["subtitle"]))
    return s


def write_pdf(path, story, styles):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    doc = SimpleDocTemplate(path, pagesize=A4,
                            leftMargin=1.2 * cm, rightMargin=1.2 * cm,
                            topMargin=1.2 * cm, bottomMargin=1.2 * cm)
    doc.build(story)


def main():
    fn = register_font()
    styles = build_styles(fn)

    write_pdf(OUTPUT, build_story(styles), styles)
    print(f"总表 PDF 已生成: {OUTPUT}")

    os.makedirs(MEMBER_OUTPUT_DIR, exist_ok=True)
    for code, (name, _) in TEAM.items():
        path = os.path.join(MEMBER_OUTPUT_DIR, f"任务清单_{name}.pdf")
        write_pdf(path, build_person_story(styles, code), styles)
        print(f"个人 PDF 已生成: {path}")


if __name__ == "__main__":
    main()
