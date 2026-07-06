# -*- coding: utf-8 -*-
"""生成小学期项目详细任务分工表 PDF"""

import os
from datetime import date

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
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

OUTPUT = os.path.join(os.path.dirname(__file__), "docs", "项目任务分工表.pdf")
FONT_PATH = r"C:\Windows\Fonts\msyh.ttc"
FONT_NAME = "MicrosoftYaHei"


def register_font():
    if os.path.exists(FONT_PATH):
        pdfmetrics.registerFont(TTFont(FONT_NAME, FONT_PATH, subfontIndex=0))
        return FONT_NAME
    raise FileNotFoundError(f"未找到中文字体: {FONT_PATH}")


def build_styles(font_name):
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title",
            fontName=font_name,
            fontSize=18,
            leading=24,
            alignment=TA_CENTER,
            spaceAfter=12,
            textColor=colors.HexColor("#1a365d"),
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            fontName=font_name,
            fontSize=11,
            leading=16,
            alignment=TA_CENTER,
            spaceAfter=16,
            textColor=colors.HexColor("#4a5568"),
        ),
        "h1": ParagraphStyle(
            "h1",
            fontName=font_name,
            fontSize=14,
            leading=20,
            spaceBefore=14,
            spaceAfter=8,
            textColor=colors.HexColor("#2c5282"),
        ),
        "h2": ParagraphStyle(
            "h2",
            fontName=font_name,
            fontSize=12,
            leading=18,
            spaceBefore=10,
            spaceAfter=6,
            textColor=colors.HexColor("#2d3748"),
        ),
        "body": ParagraphStyle(
            "body",
            fontName=font_name,
            fontSize=9.5,
            leading=15,
            spaceAfter=6,
        ),
        "small": ParagraphStyle(
            "small",
            fontName=font_name,
            fontSize=8.5,
            leading=13,
            textColor=colors.HexColor("#4a5568"),
        ),
        "cell": ParagraphStyle(
            "cell",
            fontName=font_name,
            fontSize=8,
            leading=12,
        ),
        "cell_bold": ParagraphStyle(
            "cell_bold",
            fontName=font_name,
            fontSize=8,
            leading=12,
            textColor=colors.HexColor("#1a365d"),
        ),
    }


def make_table(data, col_widths, styles, header_rows=1):
    wrapped = []
    for r, row in enumerate(data):
        new_row = []
        for c, cell in enumerate(row):
            if isinstance(cell, str):
                if r < header_rows:
                    new_row.append(Paragraph(f"<b>{cell}</b>", styles["cell_bold"]))
                else:
                    new_row.append(Paragraph(cell.replace("\n", "<br/>"), styles["cell"]))
            else:
                new_row.append(cell)
        wrapped.append(new_row)

    table = Table(wrapped, colWidths=col_widths, repeatRows=header_rows)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, header_rows - 1), colors.HexColor("#ebf4ff")),
        ("TEXTCOLOR", (0, 0), (-1, header_rows - 1), colors.HexColor("#1a365d")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for i in range(header_rows, len(data)):
        if i % 2 == 0:
            style_cmds.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f7fafc")))
    table.setStyle(TableStyle(style_cmds))
    return table


def build_story(styles):
    story = []
    story.append(Paragraph("软件工程学期实训 II", styles["title"]))
    story.append(Paragraph("实时视频分析监测系统 — 详细任务分工表", styles["title"]))
    story.append(
        Paragraph(
            f"实训周期：2026/7/6 — 7/15　|　应用场景：<b>人脸识别开锁</b>　|　技术方案：Vue3 + 全 Flask + Nginx-RTMP　|　编制日期：{date.today()}",
            styles["subtitle"],
        )
    )

    story.append(Paragraph("一、项目概述与已定方案", styles["h1"]))
    story.append(
        Paragraph(
            "<b>应用场景：人脸识别开锁（智慧门禁）</b>。在门禁摄像头前，已注册用户刷脸通过则系统下发开锁指令（前端模拟门锁状态）；"
            "陌生人刷脸则拒绝开锁并触发告警。配合门禁区域闯入检测、尾随进入、门口异常停留等能力，构成完整门禁安防系统。",
            styles["body"],
        )
    )
    story.append(
        Paragraph(
            "技术方案：全 Flask 单体后端；推拉流采用 RTMP 推流 + Flask 拉流 + MJPEG 展示；"
            "目标检测采用 OpenCV HOG + 门禁区域几何判断（YOLO 可选升级）。",
            styles["body"],
        )
    )

    scenario_data = [
        ["业务场景", "系统行为", "对应验收模块"],
        ["已注册用户刷脸", "识别成功 → 绿框 → 下发开锁 → 记录通行日志", "人脸识别 12 分"],
        ["陌生人刷脸", "识别失败 → 红框 → 拒绝开锁 → 告警 FACE_UNKNOWN", "人脸识别 12 分"],
        ["非授权人员进入门禁区", "闯入/过近/停留超 X 秒 → 告警", "目标检测 25 分"],
        ["门口多人/尾随进入", "同帧多人脸或连续两人 → 告警 TAILGATE", "视频检测 20 分"],
        ["门口长时间徘徊", "未认证人员在门前停留 X 秒 → 告警 LOITER", "视频检测 20 分"],
        ["所有告警事件", "告警中心展示、处置、日志、回放", "告警中心 8 分"],
    ]
    story.append(Spacer(1, 4))
    story.append(Paragraph("1.1 应用场景与功能映射", styles["h2"]))
    story.append(make_table(scenario_data, [3.5 * cm, 5.5 * cm, 4 * cm], styles))

    arch_data = [
        ["层级", "技术选型", "端口", "职责"],
        ["前端", "Vue3 + Vite + Element Plus", "5173 / 80", "门禁监控页、人脸录入、门锁状态、区域配置、告警中心"],
        ["后端", "Flask + Blueprint 模块化", "5000", "视频拉流、AI 分析、用户/告警/区域 API、Swagger"],
        ["数据库", "MySQL + Flask-SQLAlchemy", "3306", "用户、人脸绑定、门禁区域、通行/告警记录"],
        ["流媒体", "Nginx + RTMP 模块", "9090", "接收手机/OBS 推流、可选录像"],
        ["认证", "Flask-JWT-Extended", "—", "登录鉴权"],
        ["API 文档", "flask-restx", "/api/docs", "Swagger 接口文档（可选加分）"],
        ["CI/CD", "Gitee + Jenkins", "8099", "Push 自动构建部署（可选加分）"],
    ]
    story.append(make_table(arch_data, [2.2 * cm, 4.5 * cm, 2 * cm, 7.3 * cm], styles))
    story.append(Spacer(1, 8))

    story.append(Paragraph("二、验收分值对照（依据任务清单）", styles["h1"]))
    score_data = [
        ["模块", "类型", "分值", "最低完成标准"],
        ["1. 人脸识别", "基础", "12", "人脸注册 + 实时识别 + 陌生人告警 + 存储人脸信息"],
        ["　↳ 防欺骗认证", "可选", "+8", "防御静态图/视频/换脸等（后期扩展）"],
        ["2. 目标检测", "基础", "25", "前端画危险区 + 闯入/过近告警 + 距离/停留时间可配置"],
        ["3. 实时视频检测", "基础", "20", "至少 2 种异常活动/情况检测并告警"],
        ["　↳ 异常声学", "可选", "+8", "打架/尖叫等声音检测（不做）"],
        ["4. 告警中心", "基础", "8", "事件展示 + 处置 + 监控日志 + 事件回放"],
        ["　↳ 钉钉逐级上报", "可选", "+3", "告警推送钉钉并@责任人（后期扩展）"],
        ["　↳ AI 监控日报", "可选", "+2", "自动生成监控日报（不做）"],
        ["5. 项目基础建设", "基础", "3", "Gitee 分支/Network/贡献统计/真实姓名.md"],
        ["　↳ OpenSpec", "可选", "+5", "规范驱动开发（可选）"],
        ["　↳ Swagger", "可选", "+3", "flask-restx 真实使用并提交文档"],
        ["　↳ Jenkins CI/CD", "可选", "+4", "自动化流水线，全员会使用"],
        ["6. 沙盘验证", "可选", "待定", "待确认设备"],
        ["文档交付物", "基础", "10", "工作日报 + 需求设计文档 + 演示视频"],
        ["基础功能合计", "—", "78", "—"],
        ["可选扩展合计", "—", "33", "按完成度加分"],
    ]
    story.append(make_table(score_data, [3.2 * cm, 1.5 * cm, 1.2 * cm, 11.1 * cm], styles))
    story.append(Spacer(1, 8))

    story.append(Paragraph("三、团队成员与角色分工", styles["h1"]))
    story.append(
        Paragraph(
            "请将「成员」列替换为真实姓名。<b>文档类工作全部由 F 一人负责</b>；组长 A 承担具体开发任务，"
            "仅保留晨会主持与进度协调（不占主要工时）。各模块负责人向 F 提供素材，F 统一写入文档。",
            styles["small"],
        )
    )
    role_data = [
        ["代号", "成员", "角色", "核心职责", "Git 分支"],
        [
            "A",
            "（填写）",
            "组长 + Git/部署/回放",
            "Gitee 仓库与分支规范、deploy 部署脚本、Jenkins CI/CD、"
            "告警截图保存、监控日志 API、事件回放 API；晨会主持",
            "feature/infra\nfeature/replay",
        ],
        [
            "B",
            "（填写）",
            "流媒体 + Flask 骨架",
            "云服务器、Nginx-RTMP、Flask app.py 骨架、video 模块、生产 Nginx 反代",
            "feature/nginx\nfeature/flask-core",
        ],
        ["C", "（填写）", "AI — 人脸识别/开锁", "dlib 识别、人脸注册、陌生人告警、识别成功触发开锁 API", "feature/face"],
        ["D", "（填写）", "AI — 门禁区域/异常", "门禁区闯入/过近/停留、尾随检测、门口徘徊检测", "feature/detection"],
        ["E", "（填写）", "Flask 业务后端", "auth/users/zones/alerts 模块、MySQL 模型、Swagger、告警入库", "feature/business"],
        [
            "F",
            "（填写）",
            "前端 + 文档专员",
            "Vue 门禁页（视频+门锁状态）、人脸录入、联调；<b>全部文档</b>（日报、v1.0→v3.0、总结报告）",
            "feature/frontend\ndocs/",
        ],
    ]
    story.append(make_table(role_data, [1 * cm, 1.8 * cm, 2.5 * cm, 7.5 * cm, 3.2 * cm], styles))
    story.append(Spacer(1, 6))

    story.append(Paragraph("3.1 组长 A — 具体开发任务清单", styles["h2"]))
    leader_data = [
        ["子任务", "优先级", "交付物", "截止"],
        ["创建 Gitee 仓库、README、.gitignore", "P0", "仓库链接", "7/6"],
        ["制定分支策略 main/dev/feature/* + CONTRIBUTORS.md", "P0", "Git 规范 + 姓名对照表", "7/7"],
        ["编写 deploy/deploy-flask.sh、deploy-frontend.sh", "P0", "一键部署脚本", "7/10"],
        ["搭建 Jenkins Docker + Gitee Webhook（与 B 协作）", "P1", "8099 可自动构建", "7/11"],
        ["实现 snapshot_service：告警触发时保存截图", "P0", "services/snapshot_service.py", "7/11"],
        ["实现 /api/logs 监控日志查询 API", "P0", "blueprints/logs.py", "7/12"],
        ["实现 /api/replay/{alert_id} 事件回放 API", "P1", "关联截图 + RTMP 录像路径", "7/13"],
        ["【可选】OpenSpec 规范驱动开发目录", "P2", "openspec/", "7/12"],
        ["代码合并至 main、维护发布标签", "P0", "中期/结题 tag", "7/11/7/15"],
    ]
    story.append(make_table(leader_data, [5.5 * cm, 1.2 * cm, 5.5 * cm, 1.8 * cm], styles, header_rows=1))
    story.append(Spacer(1, 6))

    story.append(Paragraph("3.2 文档专员 F — 全部文档类任务（一人负责）", styles["h2"]))
    doc_role_data = [
        ["文档任务", "优先级", "交付物", "截止", "素材供稿"],
        ["每日工作日报撰写并提交飞书", "P0", "工作日报-MMDD", "7/6 起每晚", "全组 orally 反馈"],
        ["产品需求与设计文档 v1.0", "P0", "立项评审材料", "7/8 中午", "B/C/D/E 供技术素材"],
        ["产品需求与设计文档 v2.0", "P0", "中期评审材料", "7/11 中午", "全组供模块说明"],
        ["产品需求与设计文档 v3.0（最终版）", "P0", "结题材料", "7/15", "全组供最终截图"],
        ["项目组总结报告 + 汇总个人总结", "P0", "Word/PDF", "7/15", "全组每人交 1 页"],
        ["系统演示视频录制与剪辑", "P0", "MP4 5–10min", "7/14", "全组配合演示"],
        ["文档内架构图、界面截图、ER 图排版", "P0", "嵌入 v1.0→v3.0", "随版本", "E 供 ER，B 供架构"],
    ]
    story.append(make_table(doc_role_data, [3.8 * cm, 1 * cm, 3.2 * cm, 1.8 * cm, 3.2 * cm], styles))
    story.append(Spacer(1, 8))

    story.append(Paragraph("四、功能模块详细任务分解", styles["h1"]))

    story.append(Paragraph("4.1 模块一：人脸识别开锁（12 分 + 可选 8 分）", styles["h2"]))
    face_data = [
        ["子任务", "负责人", "优先级", "交付物", "截止"],
        ["下载 dlib 模型（shape_predictor、resnet）", "C", "P0", "dat/ 目录模型文件", "7/7"],
        ["实现 /api/face/register 人脸注册 API", "C + E", "P0", "POST 接口 + 与用户绑定", "7/9"],
        ["前端人脸录入页（绑定用户/学号）", "F", "P0", "FaceRegister.vue", "7/10"],
        ["视频流实时人脸识别 + 128 维编码比对", "C", "P0", "gen_frames 集成人脸逻辑", "7/10"],
        ["识别成功 → POST /api/door/unlock 下发开锁", "C + E", "P0", "unlock API + 通行日志", "7/10"],
        ["前端门锁状态组件（已开/已锁/拒绝）", "F", "P0", "DoorLock.vue 动画/图标", "7/11"],
        ["陌生人 → 拒绝开锁 + 告警 FACE_UNKNOWN", "C + E", "P0", "红框 + alert 入库", "7/11"],
        ["已注册人员绿框 + 显示姓名", "C", "P0", "视频流标注", "7/11"],
        ["【可选】防照片/视频/换脸欺骗（活体检测）", "C", "P2", "随机动作序列或 blink 检测", "7/14"],
    ]
    story.append(make_table(face_data, [4.5 * cm, 1.5 * cm, 1.2 * cm, 5.5 * cm, 1.8 * cm], styles))
    story.append(Spacer(1, 6))

    story.append(Paragraph("4.2 模块二：门禁区域检测（25 分）", styles["h2"]))
    story.append(
        Paragraph(
            "将「危险区域」定义为<b>门禁限定区域</b>（门前识别区/仅授权可进入区）。管理员在前端画出门禁有效区域及安全距离。",
            styles["small"],
        )
    )
    zone_data = [
        ["子任务", "负责人", "优先级", "交付物", "截止"],
        ["zone 表 + /api/zones CRUD（门禁区域）", "E", "P0", "MySQL 表 + REST API", "7/9"],
        ["前端 Canvas 画门禁区域 + 安全距离/停留阈值配置", "F + E", "P0", "ZoneEditor.vue", "7/10"],
        ["检测模块读取门禁区域配置", "D + B", "P0", "detection_service 读 zones", "7/10"],
        ["行人检测（OpenCV HOG）", "D", "P0", "detection_service.py", "7/11"],
        ["非授权闯入：未识别成功即进入区域 → 告警", "D + E", "P0", "alert type=INTRUSION", "7/11"],
        ["过近检测：距门禁区边缘 < X px → 告警", "D", "P0", "safe_distance 可配置", "7/12"],
        ["停留检测：门前停留 > X 秒未认证 → 告警", "D", "P1", "dwell_time 可配置", "7/13"],
        ["【可选】YOLOv8n 替换 HOG", "D", "P2", "提升行人检测准确率", "7/14"],
    ]
    story.append(make_table(zone_data, [4.5 * cm, 1.5 * cm, 1.2 * cm, 5.5 * cm, 1.8 * cm], styles))
    story.append(Spacer(1, 6))

    story.append(Paragraph("4.3 模块三：门禁异常检测（20 分，需 2 种）", styles["h2"]))
    story.append(
        Paragraph(
            "门禁场景下 2 种异常：<b>① 尾随进入（TAILGATE）</b>— 一次识别成功后短时间出现第二张人脸或未识别人脸进入；"
            "<b>② 门口异常徘徊（LOITER）</b>— 未认证人员在门前停留超过配置阈值。",
            styles["small"],
        )
    )
    detect_data = [
        ["子任务", "负责人", "优先级", "交付物", "截止"],
        ["确定 2 种异常方案（供 F 写入 v1.0）", "D", "P0", "尾随 + 徘徊方案说明", "7/7"],
        ["异常 1：尾随检测（同帧多人 / 连续未授权人脸）", "D", "P0", "alert type=TAILGATE", "7/12"],
        ["异常 2：门口徘徊（停留超 X 秒未开锁）", "D", "P0", "alert type=LOITER", "7/13"],
        ["【可选】强行开门模拟（画面剧烈晃动检测）", "D", "P2", "alert type=FORCE", "7/14"],
        ["【不做】跌倒/抽烟/ADAS/声学检测", "—", "—", "—", "—"],
    ]
    story.append(make_table(detect_data, [4.5 * cm, 1.5 * cm, 1.2 * cm, 5.5 * cm, 1.8 * cm], styles))
    story.append(Spacer(1, 6))

    story.append(Paragraph("4.4 模块四：告警中心（8 分 + 可选 5 分）", styles["h2"]))
    alert_data = [
        ["子任务", "负责人", "优先级", "交付物", "截止"],
        ["alert 数据表设计 + 模型", "E", "P0", "SQL + SQLAlchemy Model", "7/9"],
        ["POST /api/alerts 内部写入（检测模块调用）", "E", "P0", "alert_service.py", "7/10"],
        ["GET /api/alerts 列表（分页、类型/时间筛选）", "E", "P0", "REST API", "7/11"],
        ["PUT /api/alerts/{id}/handle 告警处置", "E", "P0", "状态 pending→handled", "7/12"],
        ["前端告警中心页（列表 + 详情 + 处置按钮）", "F", "P0", "AlertCenter.vue", "7/12"],
        ["监控日志：告警记录持久化 + 查询", "E + A", "P0", "alert 表 + /api/logs", "7/13"],
        ["事件回放：关联告警截图/录像片段", "A + F", "P1", "replay API + Replay.vue", "7/14"],
        ["【可选】钉钉 Webhook 推送 + @责任人", "E", "P2", "钉钉机器人集成", "7/14"],
        ["【可选】AI 自动生成监控日报", "—", "P3", "不做", "—"],
    ]
    story.append(make_table(alert_data, [4.5 * cm, 1.5 * cm, 1.2 * cm, 5.5 * cm, 1.8 * cm], styles))
    story.append(Spacer(1, 6))

    story.append(Paragraph("4.5 模块五：推拉流与视频展示", styles["h2"]))
    stream_data = [
        ["子任务", "负责人", "优先级", "交付物", "截止"],
        ["租用 Linux 云服务器 + 安全组放行端口", "B", "P0", "9090/5000/80", "7/6"],
        ["编译安装 Nginx-RTMP（9090 推流）", "B", "P0", "nginx.conf + 推流 demo", "7/7"],
        ["Flask /video_feed/{id} MJPEG 拉流", "B", "P0", "video.py Blueprint", "7/8"],
        ["前端门禁主页（视频流 + 门锁状态 + 通行记录）", "F", "P0", "DoorMonitor.vue", "7/11"],
        ["告警触发时保存截图至 snapshot_service", "A", "P0", "告警记录含 snapshot_path", "7/11"],
        ["生产 Nginx 反代（/api、/video_feed、静态前端）", "B", "P1", "统一 80 端口", "7/13"],
    ]
    story.append(make_table(stream_data, [4.5 * cm, 1.5 * cm, 1.2 * cm, 5.5 * cm, 1.8 * cm], styles))
    story.append(Spacer(1, 6))

    story.append(Paragraph("4.6 模块六：Flask 业务与用户管理", styles["h2"]))
    biz_data = [
        ["子任务", "负责人", "优先级", "交付物", "截止"],
        ["Flask 项目骨架 + Blueprint 注册", "B + E", "P0", "app.py + blueprints/", "7/7"],
        ["user 表 + /api/auth/login JWT 登录", "E", "P0", "auth.py", "7/9"],
        ["access_log 通行记录表 + /api/access/logs", "E", "P0", "记录开锁/拒绝/用户", "7/11"],
        ["/api/users CRUD 用户管理", "E", "P1", "users.py", "7/10"],
        ["前端登录页 + 路由守卫", "F", "P0", "Login.vue + router", "7/9"],
        ["flask-restx Swagger 文档 /api/docs", "E", "P1", "可访问 Swagger UI", "7/11"],
        ["Flask-CORS / Vite proxy 联调配置", "E + F", "P0", "vite.config.js", "7/9"],
    ]
    story.append(make_table(biz_data, [4.5 * cm, 1.5 * cm, 1.2 * cm, 5.5 * cm, 1.8 * cm], styles))
    story.append(Spacer(1, 6))

    story.append(Paragraph("4.7 模块七：项目基础建设（3 分 + 可选 12 分）", styles["h2"]))
    infra_data = [
        ["子任务", "负责人", "优先级", "交付物", "截止"],
        ["创建 Gitee 仓库 + README + .gitignore", "A", "P0", "仓库链接", "7/6"],
        ["分支策略 main/dev/feature/*", "A", "P0", "分支规范文档", "7/7"],
        ["CONTRIBUTORS.md（Git 昵称↔真实姓名）", "A", "P0", "根目录 md 文件", "7/11"],
        ["全员 commit 使用真实姓名", "全组", "P0", "Gitee 贡献统计", "全程"],
        ["【可选】OpenSpec 规范驱动开发", "A", "P2", "openspec/ 目录", "7/12"],
        ["【可选】Jenkins Docker + Gitee Webhook", "B + A", "P1", "8099 Jenkins", "7/11"],
        ["【可选】前端 + Flask 自动部署 Pipeline", "A + B", "P1", "2 个 Jenkins Job", "7/13"],
    ]
    story.append(make_table(infra_data, [4.5 * cm, 1.5 * cm, 1.2 * cm, 5.5 * cm, 1.8 * cm], styles))

    story.append(PageBreak())

    story.append(Paragraph("五、按日进度计划（7/6 — 7/15）", styles["h1"]))
    daily_data = [
        ["日期", "里程碑", "全组目标", "A", "B", "C", "D", "E", "F"],
        ["7/6 一", "项目启动", "组队定方案、建仓库", "建 Gitee\nREADME", "租服务器\n装环境", "装 Conda\ndlib demo", "调研检测\n方案", "Flask 空壳\n设计表", "Vue 空壳\n文档模板"],
        ["7/7 二", "环境就绪", "推拉流 + v1.0 初稿", "deploy 脚本\nCONTRIBUTORS", "Nginx-RTMP\n编译配置", "下载模型\n跑通 demo", "定 2 种\n异常方案", "user 表\nauth 设计", "收集素材\n写 v1.0 草稿"],
        ["7/8 三", "立项评审", "下午提交 v1.0", "snapshot\n服务设计", "推流 demo\nFlask 拉流", "人脸静态\n检测 demo", "方案素材\n给 F", "API 设计\n素材给 F", "提交 v1.0\n答辩协助"],
        ["7/9 四", "链路打通", "推流→前端可看", "deploy 脚本\n初版", "MJPEG 通\n多路流", "注册 API\n开发", "读 zone\n接口", "login API\nSwagger 规划", "登录页\n视频页\n写日报"],
        ["7/10 五", "核心开发", "人脸+用户可用", "Jenkins\n环境搭建", "Flask 骨架\n完善", "实时人脸\n识别", "HOG 行人\n检测", "users API\nalerts 表", "人脸录入页\n写日报"],
        ["7/11 六", "中期评审", "下午 v2.0+代码", "合并 main\nJenkins Job", "流媒体\n联调保障", "人脸模块\n联调", "区域检测\n初版", "Swagger\n业务 API", "提交 v2.0\n页面可演示"],
        ["7/12 日", "功能完善", "告警+异常①", "/api/logs\n日志 API", "Nginx 反代\n性能优化", "陌生人\n告警完善", "闯入+过近\n告警", "告警 CRUD", "告警中心 UI\n写日报"],
        ["7/13 一", "集成部署", "服务器部署", "replay API\nCI/CD 联调", "生产部署", "AI 模块\n部署", "异常②\n+停留检测", "数据库\n部署", "前端 build\n写 v3.0 草稿"],
        ["7/14 二", "测试文档", "全链路测试", "回放联调\n截图验收", "稳定性\n测试", "识别率\n测试", "告警触发\n测试", "Swagger\n导出给 F", "v3.0+总结\n录演示视频"],
        ["7/15 三", "结题验收", "系统演示", "Git 截图\n材料打包", "现场推流\n保障", "人脸演示", "检测演示", "后端保障", "提交全部\n文档+视频"],
    ]
    story.append(
        make_table(
            daily_data,
            [1.3 * cm, 1.8 * cm, 2.5 * cm, 1.7 * cm, 1.7 * cm, 1.7 * cm, 1.7 * cm, 1.7 * cm, 1.7 * cm],
            styles,
        )
    )
    story.append(Spacer(1, 10))

    story.append(Paragraph("六、里程碑交付清单", styles["h1"]))
    milestone_data = [
        ["节点", "时间", "交付物", "负责人"],
        ["立项评审", "7/8 下午", "产品需求与设计文档 v1.0", "F 撰写提交；全组供技术素材"],
        ["中期评审", "7/11 下午", "文档 v2.0 + 代码仓库链接 + 可演示系统", "F 提交文档；A 提交仓库链接"],
        ["结题验收", "7/15 全天", "系统部署演示 + 基础功能验收 + 扩展功能答辩", "A 讲解 Git/部署/回放；全组演示"],
        ["材料提交", "7/15 24:00", "源代码、v3.0、工作日报、总结报告、演示视频", "F 提交全部文档；A 提交代码链接与截图"],
    ]
    story.append(make_table(milestone_data, [2.5 * cm, 2 * cm, 7.5 * cm, 3 * cm], styles))
    story.append(Spacer(1, 8))

    story.append(Paragraph("七、文档交付物分工（10 分）— 全部由 F 一人负责", styles["h1"]))
    story.append(
        Paragraph(
            "以下文档类交付物<b>仅由 F 撰写、排版与提交</b>。其他成员在截止前向 F 提供文字/截图/接口清单等素材，"
            "不得自行修改最终文档。A 负责 Gitee 截图与代码仓库链接，供 F 嵌入文档。",
            styles["body"],
        )
    )
    doc_data = [
        ["文档", "内容", "撰写人", "素材供稿", "截止"],
        ["工作日报", "计划/进展/待办/效果数据", "F", "全组 17:00 口头反馈", "7/6 起每晚"],
        ["产品需求与设计文档 v1.0", "背景、目标、需求、技术方案、分工", "F", "B/C/D/E/A", "7/8 中午"],
        ["产品需求与设计文档 v2.0", "概要设计、模块划分、接口、库表", "F", "全组", "7/11 中午"],
        ["产品需求与设计文档 v3.0", "最终版 + 测试与部署说明", "F", "全组", "7/15"],
        ["　↳ 需求分析章节", "功能/非功能需求", "F 执笔", "C + D", "7/7"],
        ["　↳ 架构设计章节", "推拉流 + Flask 模块", "F 执笔", "B + E", "7/7"],
        ["　↳ 接口设计章节", "REST API + Swagger 导出", "F 执笔", "E", "7/10"],
        ["　↳ 数据库设计章节", "ER 图 + 表结构", "F 执笔", "E", "7/9"],
        ["系统演示视频", "完整功能演示录屏 5–10min", "F", "全组配合操作", "7/14"],
        ["项目组总结报告", "整体完成 + 个人总结汇总", "F", "全组每人 1 页", "7/15"],
        ["Gitee 管理截图", "分支/Network/贡献统计", "A 截图 → F 嵌入", "A", "7/14"],
    ]
    story.append(make_table(doc_data, [3.2 * cm, 3.8 * cm, 1.2 * cm, 2.5 * cm, 2.3 * cm], styles))
    story.append(Spacer(1, 8))

    story.append(Paragraph("八、仓库目录与 Git 分支规范", styles["h1"]))
    story.append(
        Paragraph(
            "<b>目录结构：</b>frontend/（Vue）| backend/（Flask）| nginx/（RTMP 配置）| deploy/（部署脚本）| docs/（文档）",
            styles["body"],
        )
    )
    git_data = [
        ["分支", "用途", "负责人"],
        ["main", "稳定可演示版本，结题标签", "A merge"],
        ["dev", "日常集成联调", "全组"],
        ["feature/infra", "Git 规范、deploy、Jenkins、日志/回放", "A"],
        ["feature/flask-core", "Flask 骨架 + video 模块", "B"],
        ["feature/face", "人脸识别", "C"],
        ["feature/detection", "目标/异常检测", "D"],
        ["feature/business", "用户/告警/区域/Swagger", "E"],
        ["feature/frontend", "Vue 前端", "F"],
        ["feature/nginx", "RTMP + 生产 Nginx 配置", "B"],
        ["docs/", "全部文档（不进代码分支或独立提交）", "F"],
    ]
    story.append(make_table(git_data, [3.5 * cm, 7 * cm, 3.5 * cm], styles))
    story.append(Spacer(1, 8))

    story.append(Paragraph("九、接口分工速查（Flask :5000 统一入口）", styles["h1"]))
    api_data = [
        ["模块", "接口", "方法", "负责人"],
        ["视频", "/video_feed/{stream_id}", "GET", "B"],
        ["人脸", "/api/face/register", "POST", "C"],
        ["门禁", "/api/door/unlock", "POST", "C + E"],
        ["门禁", "/api/door/status", "GET", "E"],
        ["通行", "/api/access/logs", "GET", "E"],
        ["认证", "/api/auth/login", "POST", "E"],
        ["用户", "/api/users", "CRUD", "E"],
        ["区域", "/api/zones", "CRUD", "E"],
        ["告警", "/api/alerts", "GET/POST", "E"],
        ["告警", "/api/alerts/{id}/handle", "PUT", "E"],
        ["日志", "/api/logs", "GET", "A"],
        ["回放", "/api/replay/{alert_id}", "GET", "A"],
        ["文档", "/api/docs", "GET", "E"],
    ]
    story.append(make_table(api_data, [2 * cm, 5.5 * cm, 2 * cm, 2.5 * cm], styles))
    story.append(Spacer(1, 8))

    story.append(Paragraph("十、风险与应对", styles["h1"]))
    risk_data = [
        ["风险", "影响", "应对措施", "负责人"],
        ["dlib 安装失败", "人脸模块阻塞", "conda-forge 预编译包；服务器提前装好", "C"],
        ["RTMP 推流不通", "无法演示视频", "本地 OBS+VLC 先验证；检查安全组 9090", "B"],
        ["检测来不及做 2 种", "视频检测扣分", "优先跌倒+区域闯入（闯入算目标检测）", "D"],
        ["前后端联调慢", "中期无法演示", "7/9 起 F 每天 1h 固定联调", "F"],
        ["Jenkins 配置复杂", "CI/CD 加分丢失", "7/11 前先手动 deploy.sh，后期补 Jenkins", "B"],
        ["文档来不及", "文档 10 分受损", "F 7/6 建模板；各模块 7/7 前交素材", "F"],
    ]
    story.append(make_table(risk_data, [3 * cm, 2.5 * cm, 5.5 * cm, 1.5 * cm], styles))
    story.append(Spacer(1, 10))

    story.append(Paragraph("十一、每日协作机制", styles["h1"]))
    story.append(
        Paragraph(
            "• <b>9:00 晨会（15min）</b>：昨日完成 / 今日计划 / 阻塞项（A 主持，不含文档撰写）<br/>"
            "• <b>17:00 总结（15min）</b>：各模块向 F 反馈素材；A 同步代码/部署进度<br/>"
            "• <b>晚上</b>：F 撰写并提交工作日报至飞书（格式：工作日报-MMDD）<br/>"
            "• <b>缺勤 3 次取消成绩</b>；A 负责代码合并，F 负责全部文档提交",
            styles["body"],
        )
    )
    story.append(Spacer(1, 12))
    story.append(
        Paragraph(
            "— 请在「成员」列填写真实姓名后分发全组 —",
            styles["subtitle"],
        )
    )
    return story


def main():
    font_name = register_font()
    styles = build_styles(font_name)
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    doc = SimpleDocTemplate(
        OUTPUT,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        title="实时视频分析监测系统 - 项目任务分工表",
        author="软件工程学期实训II",
    )
    doc.build(build_story(styles))
    print(f"PDF 已生成: {OUTPUT}")


if __name__ == "__main__":
    main()
