# -*- coding: utf-8 -*-
"""生成居家摄像头场景项目任务分工表 PDF"""

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


def build_story(styles):
    s = []
    s.append(Paragraph("软件工程学期实训 II", styles["title"]))
    s.append(Paragraph("home-camera-monitor 项目任务分工表", styles["title"]))
    s.append(Paragraph(
        f"应用场景：<b>居家智能摄像头监控</b>　|　{REPO_URL}<br/>"
        f"团队：牛雨昊、苏哲勋、王梓铭、李东礼、刘帅华、刘澎潮　|　{date.today()}",
        styles["subtitle"],
    ))

    s.append(Paragraph("一、项目概述", styles["h1"]))
    s.append(Paragraph(
        "通过家庭摄像头实时监控家中画面：<b>人脸识别</b>（识别家人/陌生人）、"
        "<b>人员统计</b>（当前在家人数）、<b>危险区域</b>（如厨房禁止小孩进入）、"
        "<b>异常检测</b>（积水、着火、摔倒）。技术栈：Vue3 + Flask + Nginx-RTMP + MySQL。",
        styles["body"],
    ))

    s.append(Paragraph("1.1 功能与验收对应", styles["h2"]))
    s.append(tbl([
        ["验收模块", "分值", "居家场景实现"],
        ["人脸识别", "12", "家人注册+识别+陌生人告警+人脸信息存储"],
        ["目标检测", "25", "危险区域画框+厨房禁止小孩+闯入告警"],
        ["实时视频检测", "20", "积水+着火+摔倒（3种异常/紧急情况）"],
        ["告警中心", "8", "展示+处置+日志+回放"],
        ["项目基础", "3", "GitHub 分支/Network/Contributors"],
        ["文档", "10", "日报+设计文档+演示视频"],
    ], [2.5 * cm, 1 * cm, 10 * cm], styles))
    s.append(Spacer(1, 6))

    s.append(Paragraph("1.2 核心业务场景", styles["h2"]))
    s.append(tbl([
        ["场景", "告警类型", "负责人"],
        ["识别家人", "—（绿框显示姓名）", "王梓铭"],
        ["陌生人出现", "FACE_UNKNOWN", "王梓铭"],
        ["统计当前人数", "前端 PersonStats 展示", "王梓铭+牛雨昊"],
        ["小孩进入厨房", "ZONE_INTRUSION", "李东礼"],
        ["地面积水", "FLOOD", "李东礼"],
        ["着火/明火", "FIRE", "李东礼"],
        ["人员摔倒", "FALL", "李东礼"],
    ], [3.5 * cm, 3.5 * cm, 3.5 * cm], styles))

    s.append(PageBreak())

    s.append(Paragraph("二、团队分工总览", styles["h1"]))
    s.append(tbl([
        ["代号", "姓名", "角色", "Git 分支", "核心目录"],
        ["A", "牛雨昊", "组长/前端/Git/部署", "feature/frontend\nfeature/infra", "frontend/ deploy/"],
        ["B", "苏哲勋", "流媒体+Flask骨架", "feature/nginx\nfeature/flask-core", "nginx/ video.py"],
        ["C", "王梓铭", "AI人脸/人员统计", "feature/face", "face_service home.py"],
        ["D", "李东礼", "AI区域/异常检测", "feature/detection", "detection_service.py"],
        ["E", "刘帅华", "Flask业务/DB", "feature/business", "models/ alerts zones"],
        ["F", "刘澎潮", "专职文档", "docs/", "飞书文档（不写代码）"],
    ], [0.7 * cm, 1.2 * cm, 2.5 * cm, 2.5 * cm, 4.6 * cm], styles))

    s.append(PageBreak())

    s.append(Paragraph("三、成员详细任务清单", styles["h1"]))

    person_section(s, styles, "A", [
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
        ["12", "Git 管理", "PR 审查；dev→main 合并", "中期/结题 tag", "7/11/15", "P0"],
    ])

    person_section(s, styles, "B", [
        ["1", "云服务器+RTMP", "Ubuntu；9090/80 端口", "推流成功", "7/6", "P0"],
        ["2", "nginx.conf", "RTMP live；HTTP 反代", "VLC 可拉流", "7/7", "P0"],
        ["3", "app.py 骨架", "Blueprint 注册；CORS", "import 无错", "7/7", "P0"],
        ["4", "video.py", "拉 RTMP；MJPEG 输出", "/video_feed 可看", "7/8", "P0"],
        ["5", "多摄像头", "living_room / kitchen 两路", "前端可切换", "7/9", "P0"],
        ["6", "gen_frames 框架", "预留 AI hook 给 C/D", "帧上可画框", "7/10", "P0"],
        ["7", "生产 Nginx 反代", "80 统一入口", "部署可访问", "7/13", "P1"],
    ])

    person_section(s, styles, "C", [
        ["1", "dlib 环境+模型", "dat/ 两个模型文件", "import 成功", "7/6-7/7", "P0"],
        ["2", "face_service", "检测+128维编码+比对", "静态图 demo", "7/8", "P0"],
        ["3", "家人注册 API", "POST /api/face/register 含 role", "Swagger 可测", "7/9", "P0"],
        ["4", "实时识别", "视频流绿框家人/红框陌生人", "标注正确", "7/10", "P0"],
        ["5", "人数统计", "统计帧内人脸数；分家人/陌生人", "count 准确", "7/10", "P0"],
        ["6", "home/presence API", "GET 返回 total/family/stranger", "A 前端可轮询", "7/11", "P0"],
        ["7", "陌生人告警", "未注册脸→FACE_UNKNOWN", "告警中心可见", "7/11", "P0"],
        ["8", "registered_faces.json", "member_id→encoding+role", "重启数据仍在", "7/9", "P0"],
    ])

    s.append(PageBreak())

    person_section(s, styles, "D", [
        ["1", "检测方案文档", "积水/着火/跌倒算法说明给 F", "写入 v1.0", "7/7", "P0"],
        ["2", "HOG 行人检测", "检人框用于区域判断", "可检出行人", "7/10", "P0"],
        ["3", "危险区域闯入", "识别为 child + 进厨房多边形", "ZONE_INTRUSION", "7/11", "P0"],
        ["4", "积水检测 FLOOD", "画面下部 HSV 蓝/灰大面积", "模拟积水可告警", "7/12", "P0"],
        ["5", "着火检测 FIRE", "高亮红/黄区域超阈值", "明火画面可告警", "7/12", "P0"],
        ["6", "摔倒检测 FALL", "人体框高宽比低于阈值", "蹲下/躺倒可告警", "7/13", "P0"],
        ["7", "与 face 联动", "区域闯入需知角色 child/adult", "联调通过", "7/11", "P0"],
        ["8", "【可选】YOLO", "替换 HOG 提升检人精度", "准确率提升", "7/14", "P2"],
    ])

    person_section(s, styles, "E", [
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
    ])

    person_section(s, styles, "F", [
        ["1", "文档模板+日报", "飞书 PRD 框架", "7/6 起每晚", "7/6", "P0"],
        ["2", "v1.0 立项文档", "背景/需求/架构/分工", "7/8 中午提交", "7/8", "P0"],
        ["3", "v2.0 中期文档", "概要设计/接口/库表", "7/11 中午", "7/11", "P0"],
        ["4", "v3.0 结题文档", "测试/部署/总结", "7/15 提交", "7/15", "P0"],
        ["5", "演示视频", "注册→识人→数人→禁区→异常", "5-10min MP4", "7/14", "P0"],
        ["6", "维护架构说明.md", "与代码同步更新", "持续", "持续", "P1"],
    ])

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
    s.append(tbl([
        ["日期", "节点", "牛雨昊", "苏哲勋", "王梓铭", "李东礼", "刘帅华", "刘澎潮"],
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
    ], [0.85 * cm, 0.85 * cm, 1.8 * cm, 1.8 * cm, 1.8 * cm, 1.8 * cm, 1.8 * cm, 1.8 * cm], styles))

    s.append(Spacer(1, 6))
    s.append(Paragraph("5.1 结题演示流程", styles["h2"]))
    s.append(Paragraph(
        "1. 注册家庭成员（爸爸/妈妈/小孩）→ 2. 客厅显示人数统计 → 3. 陌生人出现告警 → "
        "4. 小孩进入厨房禁区告警 → 5. 模拟积水/着火/摔倒告警 → 6. 告警中心处置与回放",
        styles["body"],
    ))

    s.append(Spacer(1, 8))
    s.append(Paragraph("六、协作规范", styles["h1"]))
    s.append(Paragraph(
        "• 9:00 晨会（牛雨昊）　• 17:00 向刘澎潮反馈文档素材　• feature/* → dev → main<br/>"
        "• 前端仅 A 修改 frontend/　• 文档仅 F 撰写　• Commit 用真实姓名",
        styles["body"],
    ))
    s.append(Spacer(1, 8))
    s.append(Paragraph(REPO_URL, styles["subtitle"]))
    return s


def main():
    fn = register_font()
    styles = build_styles(fn)
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    doc = SimpleDocTemplate(OUTPUT, pagesize=A4,
                            leftMargin=1.2 * cm, rightMargin=1.2 * cm,
                            topMargin=1.2 * cm, bottomMargin=1.2 * cm)
    doc.build(build_story(styles))
    print(f"PDF 已生成: {OUTPUT}")


if __name__ == "__main__":
    main()
