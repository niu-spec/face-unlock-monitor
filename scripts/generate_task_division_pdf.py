# -*- coding: utf-8 -*-
"""生成小学期项目详细任务分工表 PDF（对齐 GitHub 仓库结构）"""

import os
from datetime import date

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUT = os.path.join(ROOT, "docs", "项目任务分工表.pdf")
REPO_URL = "https://github.com/niu-spec/face-unlock-monitor"
FONT_PATH = r"C:\Windows\Fonts\msyh.ttc"
FONT_NAME = "MicrosoftYaHei"


def register_font():
    if os.path.exists(FONT_PATH):
        pdfmetrics.registerFont(TTFont(FONT_NAME, FONT_PATH, subfontIndex=0))
        return FONT_NAME
    raise FileNotFoundError(f"未找到中文字体: {FONT_PATH}")


def build_styles(font_name):
    return {
        "title": ParagraphStyle(
            "title", fontName=font_name, fontSize=18, leading=24,
            alignment=TA_CENTER, spaceAfter=10, textColor=colors.HexColor("#1a365d"),
        ),
        "subtitle": ParagraphStyle(
            "subtitle", fontName=font_name, fontSize=10, leading=15,
            alignment=TA_CENTER, spaceAfter=14, textColor=colors.HexColor("#4a5568"),
        ),
        "h1": ParagraphStyle(
            "h1", fontName=font_name, fontSize=14, leading=20,
            spaceBefore=12, spaceAfter=6, textColor=colors.HexColor("#2c5282"),
        ),
        "h2": ParagraphStyle(
            "h2", fontName=font_name, fontSize=11, leading=16,
            spaceBefore=8, spaceAfter=4, textColor=colors.HexColor("#2d3748"),
        ),
        "body": ParagraphStyle(
            "body", fontName=font_name, fontSize=9.5, leading=14, spaceAfter=6,
        ),
        "small": ParagraphStyle(
            "small", fontName=font_name, fontSize=8.5, leading=12,
            textColor=colors.HexColor("#4a5568"),
        ),
        "cell": ParagraphStyle("cell", fontName=font_name, fontSize=7.5, leading=11),
        "cell_bold": ParagraphStyle(
            "cell_bold", fontName=font_name, fontSize=7.5, leading=11,
            textColor=colors.HexColor("#1a365d"),
        ),
    }


def make_table(data, col_widths, styles, header_rows=1):
    wrapped = []
    for r, row in enumerate(data):
        new_row = []
        for cell in row:
            if isinstance(cell, str):
                style = styles["cell_bold"] if r < header_rows else styles["cell"]
                text = f"<b>{cell}</b>" if r < header_rows else cell
                new_row.append(Paragraph(text.replace("\n", "<br/>"), style))
            else:
                new_row.append(cell)
        wrapped.append(new_row)

    table = Table(wrapped, colWidths=col_widths, repeatRows=header_rows)
    cmds = [
        ("BACKGROUND", (0, 0), (-1, header_rows - 1), colors.HexColor("#ebf4ff")),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    for i in range(header_rows, len(data)):
        if i % 2 == 0:
            cmds.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f7fafc")))
    table.setStyle(TableStyle(cmds))
    return table


def build_story(styles):
    story = []
    story.append(Paragraph("软件工程学期实训 II", styles["title"]))
    story.append(Paragraph("face-unlock-monitor — 项目任务分工表", styles["title"]))
    story.append(
        Paragraph(
            f"应用场景：人脸识别开锁　|　仓库：{REPO_URL}<br/>"
            f"分支：main / dev　|　编制日期：{date.today()}",
            styles["subtitle"],
        )
    )

    # ── 1. 概述 ──
    story.append(Paragraph("一、项目概述", styles["h1"]))
    story.append(
        Paragraph(
            "本系统为智慧门禁「人脸识别开锁」方案。技术栈：Vue3 + Flask + Nginx-RTMP + MySQL。"
            "代码托管于 GitHub，目录结构已初始化；各成员按<b>仓库路径</b>认领开发任务，"
            "在对应 feature 分支提交，由 A 合并至 dev/main。",
            styles["body"],
        )
    )

    # ── 2. GitHub 仓库现状 ──
    story.append(Paragraph("二、GitHub 仓库现状（已推送）", styles["h1"]))
    repo_now = [
        ["路径", "状态", "说明", "负责人"],
        ["README.md", "✅ 已有", "项目说明、快速开始", "A"],
        ["CONTRIBUTORS.md", "✅ 已有", "GitHub 昵称 ↔ 真实姓名（待填）", "A"],
        [".gitignore", "✅ 已有", "Python/Node/venv 忽略规则", "A"],
        ["backend/app.py", "✅ 已有", "Flask 入口（/health 可测）", "B + E"],
        ["backend/requirements.txt", "✅ 已有", "Python 依赖清单", "E"],
        ["backend/blueprints/", "⬜ 空目录", "各 API 模块 Blueprint", "B/C/D/E/A"],
        ["backend/services/", "⬜ 空目录", "AI 与业务 Service 层", "C/D/E/A"],
        ["backend/models/", "⬜ 空目录", "SQLAlchemy 数据模型", "E"],
        ["backend/config.py", "⬜ 待建", "数据库/JWT/RTMP 配置", "E"],
        ["backend/dat/", "⬜ 待建", "dlib 模型（.gitignore）", "C"],
        ["frontend/", "⬜ 空目录", "Vue3 工程（待 npm init）", "A"],
        ["nginx/README.md", "✅ 已有", "RTMP 说明占位", "B"],
        ["nginx/nginx.conf", "⬜ 待建", "RTMP 9090 + HTTP 反代", "B"],
        ["deploy/deploy-flask.sh", "✅ 已有", "Flask gunicorn 部署", "A"],
        ["deploy/deploy-frontend.sh", "✅ 已有", "前端 build + Nginx 重载", "A"],
        ["docs/总体架构说明.md", "✅ 已有", "总体架构文档", "F 维护"],
        ["docs/项目任务分工表.pdf", "✅ 已有", "本文档", "F 维护"],
        ["docs/*.pdf", "✅ 已有", "课程参考 PDF ×5", "—"],
        ["scripts/", "✅ 已有", "PDF 生成等工具脚本", "A"],
    ]
    story.append(make_table(repo_now, [3.2 * cm, 1.3 * cm, 5.5 * cm, 1.5 * cm], styles))
    story.append(Spacer(1, 6))

    story.append(Paragraph("2.1 克隆与分支工作流", styles["h2"]))
    story.append(
        Paragraph(
            "<b>克隆：</b>git clone {url} → cd face-unlock-monitor → git checkout dev<br/>"
            "<b>开发：</b>git checkout -b feature/xxx → 开发 → push → 提 PR 至 dev<br/>"
            "<b>发布：</b>A 将 dev 合并至 main，打 tag（v0.1-midterm / v1.0-final）".format(url=REPO_URL),
            styles["body"],
        )
    )

    # ── 3. 团队角色 ──
    story.append(Paragraph("三、团队成员与 Git 分支", styles["h1"]))
    story.append(Paragraph("文档类工作<b>全部由 F 负责</b>；前端开发<b>全部由 A 负责</b>。", styles["small"]))
    role_data = [
        ["代号", "成员", "角色", "Git 分支", "主要仓库路径"],
        ["A", "牛雨昊", "组长/前端/Git/部署", "feature/infra\nfeature/frontend", "frontend/、deploy/、logs.py、replay.py"],
        ["B", "苏哲勋", "流媒体+Flask骨架", "feature/nginx\nfeature/flask-core", "nginx/、backend/app.py、blueprints/video.py"],
        ["C", "王梓铭", "AI人脸/开锁", "feature/face", "backend/services/face_service.py、blueprints/face.py、door.py"],
        ["D", "李东礼", "AI区域/异常", "feature/detection", "backend/services/detection_service.py"],
        ["E", "李东礼", "Flask业务/DB", "feature/business", "backend/models/、blueprints/auth|users|zones|alerts.py"],
        ["F", "刘澎潮", "专职文档专员", "docs/", "docs/、飞书文档（全部文档，不写代码）"],
    ]
    story.append(make_table(role_data, [0.8 * cm, 1.3 * cm, 2.2 * cm, 2.2 * cm, 5 * cm], styles))
    story.append(Spacer(1, 6))

    # ── 4. 按仓库路径分配任务（核心） ──
    story.append(Paragraph("四、按 GitHub 目录分配开发任务", styles["h1"]))

    story.append(Paragraph("4.1 backend/ — Flask 后端", styles["h2"]))
    backend_files = [
        ["文件路径", "负责人", "优先级", "任务说明", "截止"],
        ["backend/app.py", "B", "P0", "注册所有 Blueprint、CORS、DB 初始化", "7/7"],
        ["backend/config.py", "E", "P0", "MySQL URI、JWT Secret、RTMP 地址", "7/7"],
        ["backend/blueprints/video.py", "B", "P0", "GET /video_feed/{id} MJPEG 拉流", "7/8"],
        ["backend/blueprints/face.py", "C", "P0", "POST /api/face/register", "7/9"],
        ["backend/blueprints/door.py", "C+E", "P0", "POST /api/door/unlock、GET /api/door/status", "7/10"],
        ["backend/blueprints/auth.py", "E", "P0", "POST /api/auth/login JWT", "7/9"],
        ["backend/blueprints/users.py", "E", "P1", "用户 CRUD", "7/10"],
        ["backend/blueprints/zones.py", "E", "P0", "门禁区域 CRUD", "7/9"],
        ["backend/blueprints/alerts.py", "E", "P0", "告警列表/写入/处置", "7/11"],
        ["backend/blueprints/access.py", "E", "P0", "GET /api/access/logs 通行记录", "7/11"],
        ["backend/blueprints/logs.py", "A", "P0", "GET /api/logs 监控日志", "7/12"],
        ["backend/blueprints/replay.py", "A", "P1", "GET /api/replay/{alert_id}", "7/13"],
        ["backend/services/face_service.py", "C", "P0", "dlib 检测/编码/比对", "7/10"],
        ["backend/services/detection_service.py", "D", "P0", "HOG+区域+尾随+徘徊", "7/12"],
        ["backend/services/alert_service.py", "E", "P0", "告警统一写入", "7/10"],
        ["backend/services/snapshot_service.py", "A", "P0", "告警截图保存", "7/11"],
        ["backend/models/user.py", "E", "P0", "用户表模型", "7/7"],
        ["backend/models/zone.py", "E", "P0", "门禁区域表", "7/9"],
        ["backend/models/alert.py", "E", "P0", "告警表", "7/9"],
        ["backend/models/access_log.py", "E", "P0", "通行记录表", "7/11"],
        ["backend/registered_faces.json", "C", "P0", "人脸特征库（gitignore）", "7/9"],
        ["backend/requirements.txt", "E", "P0", "补充 flask-restx 等依赖", "7/7"],
    ]
    story.append(make_table(backend_files, [3.5 * cm, 1 * cm, 0.8 * cm, 4.2 * cm, 1.2 * cm], styles))

    story.append(Paragraph("4.2 frontend/ — Vue3 前端", styles["h2"]))
    frontend_files = [
        ["文件路径", "负责人", "优先级", "任务说明", "截止"],
        ["frontend/package.json", "A", "P0", "npm create vue@latest 初始化", "7/7"],
        ["frontend/vite.config.js", "A", "P0", "proxy /api、/video_feed → :5000", "7/9"],
        ["frontend/src/views/Login.vue", "A", "P0", "登录页", "7/9"],
        ["frontend/src/views/DoorMonitor.vue", "A", "P0", "门禁主页：视频+门锁", "7/11"],
        ["frontend/src/components/DoorLock.vue", "A", "P0", "门锁状态（开/锁/拒绝）", "7/11"],
        ["frontend/src/views/FaceRegister.vue", "A", "P0", "摄像头人脸录入", "7/10"],
        ["frontend/src/views/ZoneEditor.vue", "A", "P1", "Canvas 画门禁区域", "7/10"],
        ["frontend/src/views/AlertCenter.vue", "A", "P0", "告警列表+处置", "7/12"],
        ["frontend/src/views/AccessLog.vue", "A", "P1", "通行记录页", "7/13"],
        ["frontend/src/api/*.js", "A", "P0", "Axios 封装各 API", "7/9"],
    ]
    story.append(make_table(frontend_files, [3.8 * cm, 1 * cm, 0.8 * cm, 3.9 * cm, 1.2 * cm], styles))

    story.append(Paragraph("4.3 nginx/ + deploy/ — 部署", styles["h2"]))
    deploy_files = [
        ["文件路径", "负责人", "优先级", "任务说明", "截止"],
        ["nginx/nginx.conf", "B", "P0", "RTMP 9090 + HTTP 80 反代", "7/7"],
        ["deploy/deploy-flask.sh", "A", "P0", "完善 gunicorn 启动逻辑", "7/10"],
        ["deploy/deploy-frontend.sh", "A", "P0", "完善 npm build + rsync", "7/10"],
        ["deploy/docker-compose.yml", "A", "P2", "【可选】Jenkins 容器", "7/12"],
    ]
    story.append(make_table(deploy_files, [3.5 * cm, 1 * cm, 0.8 * cm, 4.2 * cm, 1.2 * cm], styles))

    story.append(Paragraph("4.4 docs/ + 根目录 — 文档与规范", styles["h2"]))
    docs_files = [
        ["文件路径", "负责人", "优先级", "任务说明", "截止"],
        ["CONTRIBUTORS.md", "A", "P0", "填写 6 人 GitHub 昵称与姓名", "7/6"],
        ["docs/总体架构说明.md", "F", "P0", "随开发更新架构章节", "持续"],
        ["docs/项目任务分工表.pdf", "F", "P0", "本文档，随分工更新", "7/6"],
        ["飞书：工作日报-MMDD", "F", "P0", "每日撰写提交", "7/6 起"],
        ["飞书：需求设计文档 v1.0", "F", "P0", "立项评审", "7/8 中午"],
        ["飞书：需求设计文档 v2.0", "F", "P0", "中期评审", "7/11 中午"],
        ["飞书：需求设计文档 v3.0", "F", "P0", "结题材料", "7/15"],
        ["演示视频 MP4", "F", "P0", "5–10 分钟功能演示", "7/14"],
        ["GitHub Insights 截图", "A→F", "P0", "Contributors/Network 截图嵌入 v3.0", "7/14"],
    ]
    story.append(make_table(docs_files, [3.5 * cm, 1 * cm, 0.8 * cm, 4.2 * cm, 1.2 * cm], styles))

    story.append(PageBreak())

    # ── 5. 验收分值 ──
    story.append(Paragraph("五、验收分值与场景映射", styles["h1"]))
    score_data = [
        ["模块", "分值", "门禁场景实现", "主要路径"],
        ["人脸识别", "12", "注册+识别+开锁/拒开+陌生人告警", "face_service.py、door.py"],
        ["目标检测", "25", "门禁区闯入/过近/停留", "detection_service.py、zones.py"],
        ["视频检测", "20", "尾随 TAILGATE + 徘徊 LOITER", "detection_service.py"],
        ["告警中心", "8", "展示+处置+日志+回放", "alerts.py、AlertCenter.vue、replay.py"],
        ["项目基础", "3", "GitHub 分支/Network/Contributors", "CONTRIBUTORS.md、Insights"],
        ["Swagger 可选", "+3", "flask-restx /api/docs", "app.py"],
        ["CI/CD 可选", "+4", "Jenkins + Webhook", "deploy/"],
        ["文档", "10", "日报+设计文档+演示视频", "docs/、飞书"],
    ]
    story.append(make_table(score_data, [2.5 * cm, 1 * cm, 5.5 * cm, 4.5 * cm], styles))
    story.append(Spacer(1, 8))

    # ── 6. A 与 F 专项 ──
    story.append(Paragraph("六、组长 A 具体开发任务（含前端）", styles["h1"]))
    a_tasks = [
        ["任务", "仓库路径", "截止"],
        ["邀请 5 名组员为 GitHub Collaborator", "Settings → Collaborators", "7/6"],
        ["填写 CONTRIBUTORS.md", "CONTRIBUTORS.md", "7/6"],
        ["Vue3 工程初始化 + 全部前端页面", "frontend/", "7/7–7/13"],
        ["前后端联调（vite proxy + API）", "frontend/vite.config.js", "7/9"],
        ["完善 deploy 脚本并在服务器验证", "deploy/*.sh", "7/10"],
        ["snapshot_service 告警截图", "backend/services/snapshot_service.py", "7/11"],
        ["logs / replay Blueprint", "backend/blueprints/logs.py、replay.py", "7/13"],
        ["dev → main 合并 + 打 tag", "GitHub Releases", "7/11/7/15"],
        ["【可选】Jenkins Docker + Webhook", "deploy/docker-compose.yml", "7/12"],
    ]
    story.append(make_table(a_tasks, [4.5 * cm, 5 * cm, 1.8 * cm], styles))
    story.append(Spacer(1, 6))

    story.append(Paragraph("七、文档专员 F 全部文档任务", styles["h1"]))
    story.append(Paragraph("以下<b>仅 F 撰写提交</b>，其他人 17:00 前口头反馈素材。", styles["small"]))
    f_tasks = [
        ["文档", "截止", "素材来源"],
        ["工作日报（飞书）", "每晚", "全组"],
        ["v1.0 需求设计文档", "7/8 中午", "B/C/D/E/A"],
        ["v2.0 需求设计文档", "7/11 中午", "全组"],
        ["v3.0 最终文档", "7/15", "全组"],
        ["项目组总结报告", "7/15", "每人 1 页个人总结"],
        ["系统演示视频", "7/14", "全组配合操作"],
    ]
    story.append(make_table(f_tasks, [4 * cm, 2 * cm, 6.5 * cm], styles))

    story.append(PageBreak())

    # ── 8. 日程 ──
    story.append(Paragraph("八、按日进度（7/6 — 7/15）", styles["h1"]))
    daily = [
        ["日期", "节点", "A", "B", "C", "D", "E", "F"],
        ["7/6", "启动", "Collaborators\nnpm init", "租服务器", "装 dlib", "检测方案", "config.py\nmodels/", "文档框架"],
        ["7/7", "环境", "deploy\n前端骨架", "nginx.conf\nRTMP", "dat/ 模型", "方案给 F", "auth 设计", "v1.0 草稿"],
        ["7/8", "立项", "Login 原型", "video.py\ndemo", "人脸 demo", "—", "素材给 F", "提交 v1.0"],
        ["7/9", "联调", "Login.vue\n联调", "MJPEG 通", "face/register", "—", "login API", "写日报"],
        ["7/10", "核心", "FaceRegister", "app.py 完善", "识别+unlock", "HOG demo", "alerts 表", "写日报"],
        ["7/11", "中期", "DoorMonitor\nmerge main", "联调", "陌生人告警", "区域检测", "Swagger", "提交 v2.0"],
        ["7/12", "完善", "AlertCenter\nlogs API", "Nginx 反代", "—", "闯入/过近", "告警 CRUD", "写日报"],
        ["7/13", "部署", "build+部署\nreplay API", "生产部署", "—", "尾随/徘徊", "DB 部署", "写日报"],
        ["7/14", "测试", "UI 走查\nGit 截图", "压测", "准确率", "告警测试", "Swagger 导出", "v3.0+视频"],
        ["7/15", "结题", "前端演示\n材料打包", "推流保障", "演示", "演示", "后端保障", "提交文档"],
    ]
    story.append(make_table(daily, [1.1 * cm, 1.2 * cm, 1.85 * cm, 1.85 * cm, 1.85 * cm, 1.85 * cm, 1.85 * cm, 1.85 * cm], styles))
    story.append(Spacer(1, 8))

    # ── 9. 接口速查 ──
    story.append(Paragraph("九、API 与文件对应速查", styles["h1"]))
    api_data = [
        ["接口", "方法", "Blueprint 文件", "负责人"],
        ["/video_feed/{id}", "GET", "blueprints/video.py", "B"],
        ["/api/face/register", "POST", "blueprints/face.py", "C"],
        ["/api/door/unlock", "POST", "blueprints/door.py", "C+E"],
        ["/api/door/status", "GET", "blueprints/door.py", "E"],
        ["/api/auth/login", "POST", "blueprints/auth.py", "E"],
        ["/api/zones", "CRUD", "blueprints/zones.py", "E"],
        ["/api/alerts", "GET/POST", "blueprints/alerts.py", "E"],
        ["/api/access/logs", "GET", "blueprints/access.py", "E"],
        ["/api/logs", "GET", "blueprints/logs.py", "A"],
        ["/api/replay/{id}", "GET", "blueprints/replay.py", "A"],
        ["/api/docs", "GET", "app.py (flask-restx)", "E"],
    ]
    story.append(make_table(api_data, [3.2 * cm, 1.2 * cm, 3.8 * cm, 1.3 * cm], styles))
    story.append(Spacer(1, 8))

    # ── 10. 协作 ──
    story.append(Paragraph("十、协作规范", styles["h1"]))
    story.append(
        Paragraph(
            "• <b>9:00 晨会</b>（A 主持）：昨日完成 / 今日计划 / 阻塞<br/>"
            "• <b>17:00</b>：各模块向 F 反馈文档素材<br/>"
            "• <b>Commit 规范</b>：feat/fix/docs: 描述（使用真实姓名）<br/>"
            "• <b>PR 流程</b>：feature/* → dev（Review）→ main（A merge）<br/>"
            "• <b>禁止</b>：直接 push main；F 以外成员修改最终文档；非 A 成员修改 frontend/",
            styles["body"],
        )
    )
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"仓库地址：{REPO_URL}", styles["subtitle"]))
    story.append(Paragraph("— 项目组：牛雨昊、苏哲勋、王梓铭、李东礼、刘澎潮 —", styles["subtitle"]))
    return story


def main():
    font_name = register_font()
    styles = build_styles(font_name)
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    doc = SimpleDocTemplate(
        OUTPUT, pagesize=A4,
        leftMargin=1.4 * cm, rightMargin=1.4 * cm,
        topMargin=1.4 * cm, bottomMargin=1.4 * cm,
        title="face-unlock-monitor 项目任务分工表",
    )
    doc.build(build_story(styles))
    print(f"PDF 已生成: {OUTPUT}")


if __name__ == "__main__":
    main()
