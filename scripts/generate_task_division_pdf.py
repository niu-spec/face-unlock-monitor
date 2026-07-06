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
FONT_PATH = r"C:\Windows\Fonts\msyh.ttc"
FONT_NAME = "MicrosoftYaHei"

TEAM = {
    "A": ("牛雨昊", "组长/前端/Git/部署"),
    "B": ("苏哲勋", "流媒体/Flask骨架"),
    "C": ("王梓铭", "AI人脸/人员统计"),
    "D": ("李东礼", "AI危险区域/异常检测"),
    "E": ("刘帅华", "Flask业务/数据库"),
    "F": ("刘澎潮", "专职文档"),
}

BRANCH_INFO = {
    "A": ("feature/frontend\nfeature/infra", "frontend/ deploy/"),
    "B": ("feature/nginx\nfeature/flask-core", "nginx/ backend/video.py"),
    "C": ("feature/face", "face_service home.py"),
    "D": ("feature/detection", "detection_service.py"),
    "E": ("feature/business", "models/ alerts zones"),
    "F": ("—（不写代码）", "飞书文档"),
}

TASKS = {
    "A": [
        ["1", "Vue3 工程初始化", "Element Plus + Router + Axios", "npm run dev 可访问", "7/7", "P0"],
        ["2", "HomeMonitor.vue", "多路摄像头 MJPEG；嵌入 PersonStats", "可看客厅/厨房画面", "7/11", "P0"],
        ["3", "PersonStats.vue", "展示 total/family/stranger 人数", "数字随识别更新", "7/11", "P0"],
        ["4", "FamilyRegister.vue", "录入家人+角色(adult/child)+拍照", "注册成功", "7/10", "P0"],
        ["5", "ZoneEditor.vue", "Canvas 画厨房等区域；设 forbidden_roles", "区域可保存", "7/10", "P0"],
        ["6", "AlertCenter.vue", "告警列表；按类型筛选", "可处置告警", "7/12", "P0"],
        ["7", "EventLog.vue", "事件/识别记录时间线", "可查历史", "7/13", "P1"],
        ["8", "Login.vue + api封装", "JWT 登录；vite proxy", "联调通过", "7/9", "P0"],
        ["9", "snapshot_service", "告警截图保存", "alert 含截图路径", "7/11", "P0"],
        ["10", "logs/replay API", "日志查询+事件回放", "可回看截图", "7/13", "P1"],
        ["11", "deploy 脚本", "服务器一键部署", "deploy 实测通过", "7/10", "P0"],
        ["12", "Git 管理", "PR 审查；dev→main 合并；分支保护", "中期/结题 tag", "7/11/15", "P0"],
    ],
    "B": [
        ["1", "云服务器+RTMP", "Ubuntu；9090/80 端口", "推流成功", "7/6", "P0"],
        ["2", "nginx.conf", "RTMP live；HTTP 反代", "VLC 可拉流", "7/7", "P0"],
        ["3", "app.py 骨架", "Blueprint 注册；CORS", "import 无错", "7/7", "P0"],
        ["4", "video.py", "拉 RTMP；MJPEG 输出", "/video_feed 可看", "7/8", "P0"],
        ["5", "多摄像头", "living_room / kitchen 两路", "前端可切换", "7/9", "P0"],
        ["6", "gen_frames 框架", "预留 AI hook 给 C/D", "帧上可画框", "7/10", "P0"],
        ["7", "生产 Nginx 反代", "80 统一入口", "部署可访问", "7/13", "P1"],
    ],
    "C": [
        ["1", "dlib 环境+模型", "dat/ 两个模型文件", "import 成功", "7/6-7/7", "P0"],
        ["2", "face_service", "检测+128维编码+比对", "静态图 demo", "7/8", "P0"],
        ["3", "家人注册 API", "POST /api/face/register 含 role", "Swagger 可测", "7/9", "P0"],
        ["4", "实时识别", "视频流绿框家人/红框陌生人", "标注正确", "7/10", "P0"],
        ["5", "人数统计", "统计帧内人脸数；分家人/陌生人", "count 准确", "7/10", "P0"],
        ["6", "home/presence API", "GET 返回 total/family/stranger", "A 前端可轮询", "7/11", "P0"],
        ["7", "陌生人告警", "未注册脸→FACE_UNKNOWN", "告警中心可见", "7/11", "P0"],
        ["8", "registered_faces.json", "member_id→encoding+role", "重启数据仍在", "7/9", "P0"],
    ],
    "D": [
        ["1", "检测方案文档", "积水/着火/跌倒算法说明给 F", "写入 v1.0", "7/7", "P0"],
        ["2", "HOG 行人检测", "检人框用于区域判断", "可检出行人", "7/10", "P0"],
        ["3", "危险区域闯入", "识别为 child + 进厨房多边形", "ZONE_INTRUSION", "7/11", "P0"],
        ["4", "积水检测 FLOOD", "画面下部 HSV 蓝/灰大面积", "模拟积水可告警", "7/12", "P0"],
        ["5", "着火检测 FIRE", "高亮红/黄区域超阈值", "明火画面可告警", "7/12", "P0"],
        ["6", "摔倒检测 FALL", "人体框高宽比低于阈值", "蹲下/躺倒可告警", "7/13", "P0"],
        ["7", "与 face 联动", "区域闯入需知角色 child/adult", "联调通过", "7/11", "P0"],
        ["8", "【可选】YOLO", "替换 HOG 提升检人精度", "准确率提升", "7/14", "P2"],
    ],
    "E": [
        ["1", "config.py + models", "MySQL 连接；family_member/zone/alert", "建表成功", "7/7", "P0"],
        ["2", "family_member 表", "name/role/face 关联", "CRUD 可用", "7/9", "P0"],
        ["3", "zone 表", "含 forbidden_roles 字段", "厨房禁区可配", "7/9", "P0"],
        ["4", "auth/login", "JWT 登录", "A 可登录", "7/9", "P0"],
        ["5", "zones CRUD", "GET/POST/PUT/DELETE", "A 画框可存", "7/9", "P0"],
        ["6", "alert_service", "create_alert 供 C/D 调用", "统一写库", "7/10", "P0"],
        ["7", "alerts API", "列表/处置/分页/按类型筛选", "告警中心联调", "7/11", "P0"],
        ["8", "events API", "识别/告警事件记录", "EventLog 展示", "7/11", "P0"],
        ["9", "Swagger /api/docs", "flask-restx 文档", "可访问", "7/11", "P1"],
        ["10", "MySQL 生产部署", "服务器建库", "生产可用", "7/13", "P0"],
    ],
    "F": [
        ["1", "文档模板+日报", "飞书 PRD 框架", "7/6 起每晚", "7/6", "P0"],
        ["2", "v1.0 立项文档", "背景/需求/架构/分工", "7/8 中午提交", "7/8", "P0"],
        ["3", "v2.0 中期文档", "概要设计/接口/库表", "7/11 中午", "7/11", "P0"],
        ["4", "v3.0 结题文档", "测试/部署/总结", "7/15 提交", "7/15", "P0"],
        ["5", "演示视频", "注册→识人→数人→禁区→异常", "5-10min MP4", "7/14", "P0"],
        ["6", "维护架构说明.md", "与代码同步更新", "持续", "持续", "P1"],
    ],
}

SCHEDULE = [
    ["7/6", "启动", "Vue init\nGit", "租服务器", "装dlib", "异常方案", "models", "文档模板"],
    ["7/7", "环境", "前端骨架", "RTMP通", "模型demo", "方案给F", "zone表", "v1.0草稿"],
    ["7/8", "立项", "监控页原型", "video.py", "人脸demo", "—", "素材给F", "提交v1.0"],
    ["7/9", "联调", "Login+api", "MJPEG", "face/register", "—", "login+zones", "日报"],
    ["7/10", "核心", "FamilyRegister\nZoneEditor", "gen_frames", "识别+数人", "HOG", "alerts", "日报"],
    ["7/11", "中期", "HomeMonitor\nPersonStats", "联调", "presence API", "厨房禁区", "Swagger", "v2.0"],
    ["7/12", "异常①", "AlertCenter", "Nginx反代", "—", "积水+着火", "告警CRUD", "日报"],
    ["7/13", "异常②", "EventLog\n部署", "生产环境", "—", "摔倒检测", "DB部署", "v3.0草稿"],
    ["7/14", "测试", "UI走查", "压测", "准确率", "告警测试", "Swagger导出", "视频"],
    ["7/15", "结题", "演示", "推流保障", "识人演示", "异常演示", "后端保障", "提交文档"],
]

SCHEDULE_COL = {"A": 2, "B": 3, "C": 4, "D": 5, "E": 6, "F": 7}

PERSON_APIS = {
    "A": [
        ["/api/logs", "GET", "监控日志"],
        ["/api/replay/{id}", "GET", "事件回放"],
    ],
    "B": [
        ["/video_feed/{id}", "GET", "MJPEG 实时画面"],
    ],
    "C": [
        ["/api/face/register", "POST", "{member_id,name,role,image}"],
        ["/api/home/presence", "GET", "{total,family,stranger,members[]}"],
    ],
    "D": [],
    "E": [
        ["/api/auth/login", "POST", "JWT 登录"],
        ["/api/zones", "CRUD", "含 forbidden_roles"],
        ["/api/alerts", "GET/POST", "告警列表/内部写入"],
        ["/api/alerts/{id}/handle", "PUT", "告警处置"],
        ["/api/events", "GET", "事件记录"],
        ["/api/docs", "GET", "Swagger"],
    ],
    "F": [],
}

COLLAB_SCENES = {
    "A": ["统计当前人数 → 前端 PersonStats 展示（与王梓铭协作）"],
    "C": ["统计当前人数 → 前端 PersonStats 展示（与牛雨昊协作）"],
    "D": ["危险区域闯入需与王梓铭 face 模块联动（角色 child/adult）"],
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
    header = ["序号", "任务项", "详细说明", "交付物/验收标准", "截止", "优先级"]
    story.append(tbl([header] + tasks,
                     [0.6 * cm, 3.5 * cm, 4.8 * cm, 2.8 * cm, 1.5 * cm, 1.0 * cm], styles))
    story.append(Spacer(1, 5))


def append_git_workflow(story, styles, code=None):
    story.append(Paragraph("Git 分支规范与协作流程", styles["h1"]))
    story.append(Paragraph(
        f"代码仓库：<b>{REPO_URL}</b><br/>"
        "分支已全部创建并推送，所有成员按分工在对应 feature 分支开发。",
        styles["body"],
    ))

    story.append(Paragraph("分支结构", styles["h2"]))
    story.append(tbl([
        ["分支", "用途", "谁可操作"],
        ["main", "稳定版，结题演示", "仅牛雨昊合并"],
        ["dev", "日常集成，联调基准", "PR 合并目标"],
        ["feature/*", "各人开发分支", "各成员 push"],
    ], [3 * cm, 5 * cm, 5.5 * cm], styles))

    story.append(Paragraph("分支对照表", styles["h2"]))
    branch_rows = [["成员", "Git 分支", "负责目录"]]
    for c, (name, _) in TEAM.items():
        branches, dirs = BRANCH_INFO[c]
        branch_rows.append([name, branches, dirs])
    story.append(tbl(branch_rows, [2.5 * cm, 4.5 * cm, 6.5 * cm], styles))

    if code and code != "F":
        branches, dirs = BRANCH_INFO[code]
        primary = branches.split("\n")[0]
        story.append(Paragraph("你的 Git 操作", styles["h2"]))
        story.append(Paragraph(
            f"<b>你的分支：</b>{branches.replace(chr(10), '、')}<br/>"
            f"<b>你的目录：</b>{dirs}",
            styles["body"],
        ))
        story.append(Paragraph("首次拉代码", styles["h2"]))
        story.append(Paragraph(
            f"git clone {REPO_URL}.git<br/>"
            f"cd home-camera-monitor<br/>"
            f"git checkout {primary}",
            styles["code"],
        ))
        story.append(Paragraph("日常开发", styles["h2"]))
        story.append(Paragraph(
            f"1. 同步 dev：git pull origin dev → git merge dev<br/>"
            f"2. 开发提交：git add . → git commit -m \"feat(模块): 简述\" → git push origin {primary}<br/>"
            "3. 提 PR：Base 选 <b>dev</b>，Assign 牛雨昊 Review<br/>"
            "4. 合并后再次 pull dev 保持同步",
            styles["body"],
        ))
    elif code == "F":
        story.append(Paragraph("文档协作说明", styles["h2"]))
        story.append(Paragraph(
            "你不参与 Git 代码分支。各成员每天 <b>17:00</b> 向你反馈文档素材；"
            "你负责飞书文档撰写与维护 docs/总体架构说明.md。",
            styles["body"],
        ))
    else:
        story.append(Paragraph("首次拉代码（通用）", styles["h2"]))
        story.append(Paragraph(
            f"git clone {REPO_URL}.git<br/>"
            "cd home-camera-monitor<br/>"
            "git checkout feature/你的分支名",
            styles["code"],
        ))
        story.append(Paragraph("开发流程", styles["h2"]))
        story.append(Paragraph(
            "feature/* → PR → dev →（中期 7/11 / 结题 7/15）→ main<br/>"
            "• 禁止直接 push 到 main<br/>"
            "• Commit 使用真实姓名（课程统计 Contributors）<br/>"
            "• 不要修改他人负责目录<br/>"
            "• PR 合并方式：Squash and merge",
            styles["body"],
        ))

    story.append(Paragraph("协作规范", styles["h2"]))
    story.append(Paragraph(
        "• 9:00 晨会（牛雨昊主持）<br/>"
        "• 17:00 各成员向刘澎潮反馈文档素材<br/>"
        "• 前端目录 frontend/ 仅牛雨昊修改<br/>"
        "• 中期（7/11）、结题（7/15）由牛雨昊打 tag 并合并 main",
        styles["body"],
    ))
    story.append(Spacer(1, 6))


def append_overview_sections(story, styles):
    story.append(Paragraph("一、项目概述", styles["h1"]))
    story.append(Paragraph(
        "通过家庭摄像头实时监控家中画面：<b>人脸识别</b>（识别家人/陌生人）、"
        "<b>人员统计</b>（当前在家人数）、<b>危险区域</b>（如厨房禁止小孩进入）、"
        "<b>异常检测</b>（积水、着火、摔倒）。技术栈：Vue3 + Flask + Nginx-RTMP + MySQL。",
        styles["body"],
    ))

    story.append(Paragraph("1.1 功能与验收对应", styles["h2"]))
    story.append(tbl([
        ["验收模块", "分值", "居家场景实现"],
        ["人脸识别", "12", "家人注册+识别+陌生人告警+人脸信息存储"],
        ["目标检测", "25", "危险区域画框+厨房禁止小孩+闯入告警"],
        ["实时视频检测", "20", "积水+着火+摔倒（3种异常/紧急情况）"],
        ["告警中心", "8", "展示+处置+日志+回放"],
        ["项目基础", "3", "GitHub 分支/Network/Contributors"],
        ["文档", "10", "日报+设计文档+演示视频"],
    ], [2.5 * cm, 1 * cm, 10 * cm], styles))
    story.append(Spacer(1, 6))

    story.append(Paragraph("1.2 核心业务场景", styles["h2"]))
    story.append(tbl([
        ["场景", "告警类型", "负责人"],
        ["识别家人", "—（绿框显示姓名）", "王梓铭"],
        ["陌生人出现", "FACE_UNKNOWN", "王梓铭"],
        ["统计当前人数", "前端 PersonStats 展示", "王梓铭+牛雨昊"],
        ["小孩进入厨房", "ZONE_INTRUSION", "李东礼"],
        ["地面积水", "FLOOD", "李东礼"],
        ["着火/明火", "FIRE", "李东礼"],
        ["人员摔倒", "FALL", "李东礼"],
    ], [3.5 * cm, 3.5 * cm, 3.5 * cm], styles))


def build_story(styles):
    s = []
    s.append(Paragraph("软件工程学期实训 II", styles["title"]))
    s.append(Paragraph("home-camera-monitor 项目任务分工表", styles["title"]))
    s.append(Paragraph(
        f"应用场景：<b>居家智能摄像头监控</b>　|　{REPO_URL}<br/>"
        f"团队：牛雨昊、苏哲勋、王梓铭、李东礼、刘帅华、刘澎潮　|　{date.today()}",
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
    for code in TEAM:
        person_section(s, styles, code, TASKS[code])
        if code == "C":
            s.append(PageBreak())

    s.append(PageBreak())
    s.append(Paragraph("四、API 接口清单", styles["h1"]))
    s.append(tbl([
        ["接口", "方法", "负责人", "说明"],
        ["/video_feed/{id}", "GET", "苏哲勋", "MJPEG 实时画面"],
        ["/api/face/register", "POST", "王梓铭", "{member_id,name,role,image}"],
        ["/api/home/presence", "GET", "王梓铭", "{total,family,stranger,members[]}"],
        ["/api/auth/login", "POST", "刘帅华", "JWT 登录"],
        ["/api/zones", "CRUD", "刘帅华", "含 forbidden_roles"],
        ["/api/alerts", "GET/POST", "刘帅华", "告警列表/内部写入"],
        ["/api/alerts/{id}/handle", "PUT", "刘帅华", "告警处置"],
        ["/api/events", "GET", "刘帅华", "事件记录"],
        ["/api/logs", "GET", "牛雨昊", "监控日志"],
        ["/api/replay/{id}", "GET", "牛雨昊", "事件回放"],
        ["/api/docs", "GET", "刘帅华", "Swagger"],
    ], [3 * cm, 1.2 * cm, 1.3 * cm, 6 * cm], styles))

    s.append(Paragraph("4.1 告警类型", styles["h2"]))
    s.append(tbl([
        ["type", "含义", "检测模块", "负责人"],
        ["FACE_UNKNOWN", "陌生人", "face_service", "王梓铭"],
        ["ZONE_INTRUSION", "危险区域闯入", "detection+face", "李东礼"],
        ["FLOOD", "积水", "detection_service", "李东礼"],
        ["FIRE", "着火", "detection_service", "李东礼"],
        ["FALL", "摔倒", "detection_service", "李东礼"],
    ], [2.5 * cm, 2 * cm, 3 * cm, 1.5 * cm], styles))

    s.append(PageBreak())
    s.append(Paragraph("五、按日进度（7/6 — 7/15）", styles["h1"]))
    s.append(tbl(
        [["日期", "节点", "牛雨昊", "苏哲勋", "王梓铭", "李东礼", "刘帅华", "刘澎潮"]] + SCHEDULE,
        [0.85 * cm, 0.85 * cm, 1.8 * cm, 1.8 * cm, 1.8 * cm, 1.8 * cm, 1.8 * cm, 1.8 * cm],
        styles,
    ))

    s.append(Spacer(1, 6))
    s.append(Paragraph("5.1 结题演示流程", styles["h2"]))
    s.append(Paragraph(
        "1. 注册家庭成员（爸爸/妈妈/小孩）→ 2. 客厅显示人数统计 → 3. 陌生人出现告警 → "
        "4. 小孩进入厨房禁区告警 → 5. 模拟积水/着火/摔倒告警 → 6. 告警中心处置与回放",
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
        f"Git 分支：{branches.replace(chr(10), '、')}　|　目录：{dirs}　|　{date.today()}",
        styles["subtitle"],
    ))

    append_git_workflow(s, styles, code=code)
    s.append(PageBreak())

    s.append(Paragraph("一、你的任务清单", styles["h1"]))
    header = ["序号", "任务项", "详细说明", "交付物/验收标准", "截止", "优先级"]
    s.append(tbl([header] + TASKS[code],
                 [0.6 * cm, 3.2 * cm, 4.5 * cm, 3.2 * cm, 1.5 * cm, 1.0 * cm], styles))

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
        "A": "监控主页、人数面板、告警中心、事件回放、部署演示",
        "B": "视频推流与 MJPEG 拉流保障",
        "C": "家人注册、实时识别、陌生人告警、人数统计",
        "D": "厨房禁区闯入、积水/着火/摔倒异常检测",
        "E": "登录鉴权、区域配置、告警 CRUD、Swagger 文档",
        "F": "演示视频拍摄与结题文档提交",
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
