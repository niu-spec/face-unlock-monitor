# -*- coding: utf-8 -*-
"""生成小学期项目详细任务分工表 PDF（详细版）"""

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
REPO_URL = "https://github.com/niu-spec/face-unlock-monitor"
FONT_PATH = r"C:\Windows\Fonts\msyh.ttc"
FONT_NAME = "MicrosoftYaHei"

TEAM = {
    "A": ("牛雨昊", "组长/前端/Git/部署"),
    "B": ("苏哲勋", "流媒体/Flask骨架"),
    "C": ("王梓铭", "AI人脸/开锁"),
    "D": ("李东礼", "AI区域/异常检测"),
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


def person_section(story, styles, code, tasks, col_widths=None):
    name, role = TEAM[code]
    story.append(Paragraph(f"{code} — {name}（{role}）", styles["h2"]))
    if col_widths is None:
        col_widths = [0.6 * cm, 3.8 * cm, 4.8 * cm, 2.8 * cm, 1.5 * cm, 1.0 * cm]
    header = ["序号", "任务项", "详细说明", "交付物/验收标准", "截止", "优先级"]
    story.append(tbl([header] + tasks, col_widths, styles))
    story.append(Spacer(1, 5))


def build_story(styles):
    s = []
    s.append(Paragraph("软件工程学期实训 II", styles["title"]))
    s.append(Paragraph("face-unlock-monitor 项目任务分工表（详细版）", styles["title"]))
    s.append(Paragraph(
        f"应用场景：人脸识别开锁　|　{REPO_URL}<br/>"
        f"团队：牛雨昊、苏哲勋、王梓铭、李东礼、刘帅华、刘澎潮　|　{date.today()}",
        styles["subtitle"],
    ))

    # ── 1 概述 ──
    s.append(Paragraph("一、项目概述与协作原则", styles["h1"]))
    s.append(Paragraph(
        "技术栈：Vue3 + Flask + Nginx-RTMP + MySQL。A 负责前端与 Git；F 专职文档不写代码；"
        "其余成员按 backend/ 模块开发。开发流程：feature/* → PR → dev → A 合并 main。",
        styles["body"],
    ))
    s.append(tbl([
        ["原则", "说明"],
        ["路径唯一", "每个文件只有一个主负责人，协作需提前沟通"],
        ["先通后优", "7/11 前保证可演示，优化与加分项放后期"],
        ["文档集中", "F 统一撰写；17:00 各模块口头反馈素材"],
        ["Commit 规范", "feat(模块): 描述 — 使用真实姓名"],
        ["联调节点", "7/9 首次联调；7/11 中期演示；7/14 全链路测试"],
    ], [2.5 * cm, 13 * cm], styles))
    s.append(Spacer(1, 6))

    # ── 2 团队总览 ──
    s.append(Paragraph("二、团队分工总览", styles["h1"]))
    s.append(tbl([
        ["代号", "姓名", "角色", "Git 分支", "核心目录", "工作量"],
        ["A", "牛雨昊", "组长/前端/Git/部署", "feature/infra\nfeature/frontend", "frontend/ deploy/", "★★★★★"],
        ["B", "苏哲勋", "流媒体+Flask骨架", "feature/nginx\nfeature/flask-core", "nginx/ video.py app.py", "★★★★"],
        ["C", "王梓铭", "AI人脸/开锁", "feature/face", "face_service face.py door.py", "★★★★"],
        ["D", "李东礼", "AI区域/异常", "feature/detection", "detection_service.py", "★★★★"],
        ["E", "刘帅华", "Flask业务/DB", "feature/business", "models/ auth alerts zones", "★★★★"],
        ["F", "刘澎潮", "专职文档", "docs/", "飞书文档 docs/", "★★★"],
    ], [0.7 * cm, 1.2 * cm, 2.3 * cm, 2.3 * cm, 4.5 * cm, 1.0 * cm], styles))

    s.append(PageBreak())

    # ── 3 各人详细任务 ──
    s.append(Paragraph("三、成员详细任务清单", styles["h1"]))
    s.append(Paragraph("每项任务均含验收标准。完成后在晨会汇报并在 GitHub 提交对应代码。", styles["small"]))

    person_section(s, styles, "A", [
        ["1", "邀请 GitHub Collaborator", "Settings→Collaborators 添加 5 人 Write 权限", "6 人均可 push", "7/6", "P0"],
        ["2", "完善 CONTRIBUTORS.md", "补全 B–F 的 GitHub 昵称", "6 人信息完整", "7/6", "P0"],
        ["3", "Vue3 工程初始化", "npm create vue@latest；装 Element Plus、Axios、Router", "npm run dev 可访问", "7/7", "P0"],
        ["4", "vite.config.js 代理", "proxy: /api、/video_feed → localhost:5000", "前端无 CORS 报错", "7/9", "P0"],
        ["5", "Login.vue", "用户名密码登录；Token 存 localStorage；路由守卫", "登录成功跳转主页", "7/9", "P0"],
        ["6", "DoorMonitor.vue", "MJPEG 视频 img；轮询 door/status；展示门锁", "可看到实时视频", "7/11", "P0"],
        ["7", "DoorLock.vue", "三态：locked/unlocked/denied 图标+动画", "识别成功变绿开锁", "7/11", "P0"],
        ["8", "FaceRegister.vue", "getUserMedia 摄像头；canvas 截图 base64 上传", "注册成功提示", "7/10", "P0"],
        ["9", "ZoneEditor.vue", "Canvas 画多边形；保存 points 至 /api/zones", "区域可保存回显", "7/10", "P1"],
        ["10", "AlertCenter.vue", "告警列表分页；处置按钮 PUT handle", "可查看并处置告警", "7/12", "P0"],
        ["11", "AccessLog.vue", "展示通行记录表格", "显示开锁/拒绝记录", "7/13", "P1"],
        ["12", "api/*.js 封装", "auth/face/door/alerts/zones/access 模块", "Axios 统一拦截器", "7/9", "P0"],
        ["13", "snapshot_service.py", "告警时 cv2.imwrite 保存截图", "alert 含 snapshot_path", "7/11", "P0"],
        ["14", "logs.py", "GET /api/logs 分页查告警日志", "Swagger 可测", "7/12", "P0"],
        ["15", "replay.py", "GET /api/replay/{id} 返回截图+录像路径", "前端可查看回放", "7/13", "P1"],
        ["16", "deploy 脚本完善", "服务器实测 deploy-flask/frontend.sh", "一键部署成功", "7/10", "P0"],
        ["17", "merge dev→main", "中期/结题打 tag v0.1/v1.0", "GitHub Releases 可见", "7/11/15", "P0"],
        ["18", "【可选】Jenkins", "Docker 8099 + Webhook", "push 自动部署", "7/12", "P2"],
    ])

    person_section(s, styles, "B", [
        ["1", "租用云服务器", "Ubuntu；放行 80/9090/5000/22", "SSH 可登录", "7/6", "P0"],
        ["2", "安装依赖包", "build-essential libpcre3-dev libssl-dev 等", "apt 无报错", "7/6", "P0"],
        ["3", "编译 Nginx-RTMP", "按任务说明书 configure + make install", "9090 端口监听", "7/7", "P0"],
        ["4", "nginx/nginx.conf", "RTMP live app；record flv；HTTP 9091/9092", "推流后 VLC 可拉", "7/7", "P0"],
        ["5", "推流测试", "OBS/手机推 rtmp://IP:9090/live/1", "9092 可看录像列表", "7/7", "P0"],
        ["6", "app.py 骨架", "注册 Blueprint、CORS、create_app 工厂模式", "import 无报错", "7/7", "P0"],
        ["7", "video.py", "cv2.VideoCapture 拉 RTMP；frame_skip=5；MJPEG", "浏览器可看 /video_feed/1", "7/8", "P0"],
        ["8", "多路流支持", "live/1、live/2 不同 stream_id", "前端可切换", "7/9", "P0"],
        ["9", "gen_frames 框架", "预留 hook 供 C/D 注入 AI 处理", "帧上可画框", "7/10", "P0"],
        ["10", "生产 Nginx 反代", "80 端口：/api→5000 /video_feed→5000 /→dist", "统一域名访问", "7/13", "P1"],
        ["11", "协助 Jenkins", "挂载 /service；配合 A 配 Webhook", "CI 可构建", "7/12", "P2"],
    ])

    person_section(s, styles, "C", [
        ["1", "Conda 环境", "python=3.10；conda-forge 装 dlib", "import dlib 成功", "7/6", "P0"],
        ["2", "下载模型", "shape_predictor_68 + resnet 放 backend/dat/", "dat/ 两文件存在", "7/7", "P0"],
        ["3", "face_service 初始化", "detector/sp/facerec 加载；load_registered_faces", "单测可检测人脸", "7/7", "P0"],
        ["4", "静态图 demo", "本地图片检测+编码", "立项可演示", "7/8", "P0"],
        ["5", "face.py register", "POST {user_id,image} base64；存 JSON", "Swagger/Postman 201", "7/9", "P0"],
        ["6", "实时识别", "gen_frames 中灰度→检测→128维比对", "视频流有框", "7/10", "P0"],
        ["7", "识别成功逻辑", "tolerance=0.4；绿框+姓名", "熟人显示学号", "7/10", "P0"],
        ["8", "陌生人逻辑", "红框+Stranger；调 alert_service", "告警 FACE_UNKNOWN", "7/11", "P0"],
        ["9", "door unlock 联动", "识别成功调 door_service.unlock", "前端门锁变开", "7/10", "P0"],
        ["10", "registered_faces.json", "初始 {}；与用户 ID 绑定", "重启后数据仍在", "7/9", "P0"],
        ["11", "【可选】活体检测", "眨眼/随机动作序列", "照片无法开锁", "7/14", "P2"],
    ])

    s.append(PageBreak())

    person_section(s, styles, "D", [
        ["1", "检测方案文档", "尾随+徘徊算法说明 500 字给 F", "F 写入 v1.0", "7/7", "P0"],
        ["2", "detection_service 框架", "类结构：load_zones/process_frame", "B 可 import 调用", "7/9", "P0"],
        ["3", "HOG 行人检测", "cv2.HOGDescriptor 默认行人器", "视频帧检出 person 框", "7/10", "P0"],
        ["4", "区域读取", "从 E 的 zones API 或 DB 读多边形", "能获取 points_json", "7/10", "P0"],
        ["5", "点-in-多边形", "射线法判断行人中心是否在区域内", "单元测试通过", "7/11", "P0"],
        ["6", "闯入告警 INTRUSION", "未识别成功+进入区域→alert", "告警中心可见", "7/11", "P0"],
        ["7", "过近告警 PROXIMITY", "距边缘小于 safe_distance 像素", "阈值可配置", "7/12", "P0"],
        ["8", "停留告警 LOITER", "门前 dwell_time 秒未认证", "超时触发告警", "7/13", "P0"],
        ["9", "尾随 TAILGATE", "同帧>1人脸或 unlock 后 3s 新人脸", "alert type=TAILGATE", "7/12", "P0"],
        ["10", "徘徊（与LOITER合并）", "文档中说明与停留检测关系", "满足 2 种异常", "7/13", "P0"],
        ["11", "【可选】YOLOv8n", "ultralytics 替换 HOG", "检测更准", "7/14", "P2"],
    ])

    person_section(s, styles, "E", [
        ["1", "config.py", "Dev/Prod 配置类；SQLALCHEMY_DATABASE_URI", "Flask 读配置正常", "7/7", "P0"],
        ["2", "models/user.py", "username/password_hash/student_id/role", "migrate 建表成功", "7/7", "P0"],
        ["3", "models/zone.py", "name/stream_id/points_json/safe_distance/dwell_time", "CRUD 可用", "7/9", "P0"],
        ["4", "models/alert.py", "type/level/stream_id/status/snapshot_path", "可写入查询", "7/9", "P0"],
        ["5", "models/access_log.py", "user_id/result/stream_id/created_at", "开锁自动写入", "7/11", "P0"],
        ["6", "auth.py login", "POST {username,password}→JWT", "返回 access_token", "7/9", "P0"],
        ["7", "users.py CRUD", "管理员增删改查用户", "Swagger 文档完整", "7/10", "P1"],
        ["8", "zones.py CRUD", "GET/POST/PUT/DELETE /api/zones", "A 前端可调用", "7/9", "P0"],
        ["9", "alert_service.py", "create_alert(type,desc,...) 供 C/D 调用", "内部函数不写 HTTP", "7/10", "P0"],
        ["10", "alerts.py API", "GET 列表分页；PUT handle；POST 内部写入", "告警中心联调", "7/11", "P0"],
        ["11", "door.py status", "GET /api/door/status 返回 locked/unlocked", "A 轮询可用", "7/10", "P0"],
        ["12", "access.py logs", "GET /api/access/logs 通行记录", "AccessLog.vue 展示", "7/11", "P0"],
        ["13", "flask-restx Swagger", "app.py 注册 Api；各 Blueprint 加 doc", "/api/docs 可访问", "7/11", "P1"],
        ["14", "requirements.txt", "补充 flask-sqlalchemy/jwt/cors/restx/pymysql", "pip install 成功", "7/7", "P0"],
        ["15", "MySQL 部署", "服务器建库建表；提供连接串给 B", "生产 DB 可用", "7/13", "P0"],
    ])

    person_section(s, styles, "F", [
        ["1", "文档模板", "从飞书复制 PRD 模板建目录", "章节框架完整", "7/6", "P0"],
        ["2", "工作日报", "计划/进展/待办/效果；每晚提交", "工作日报-MMDD", "7/6起", "P0"],
        ["3", "v1.0 背景目标", "门禁场景+项目意义", "7/8 立项", "7/7", "P0"],
        ["4", "v1.0 需求分析", "素材：C/D 功能说明", "功能列表+用例", "7/7", "P0"],
        ["5", "v1.0 技术方案", "素材：B/E 架构说明", "架构图+技术栈", "7/7", "P0"],
        ["6", "v1.0 分工", "本文档 PDF 嵌入", "6 人职责清晰", "7/8", "P0"],
        ["7", "v2.0 概要设计", "模块划分+接口+库表", "中期评审", "7/11", "P0"],
        ["8", "v3.0 最终文档", "测试+部署+总结", "结题提交", "7/15", "P0"],
        ["9", "总结报告", "汇总 6 人个人总结各 1 页", "项目组总结", "7/15", "P0"],
        ["10", "演示视频", "5–10min：注册→刷脸→告警→区域", "MP4 上传", "7/14", "P0"],
        ["11", "维护 docs/", "架构说明.md 随版本更新", "与代码一致", "持续", "P1"],
    ])

    s.append(PageBreak())

    # ── 4 模块验收 ──
    s.append(Paragraph("四、功能模块验收标准（对照任务清单）", styles["h1"]))

    s.append(Paragraph("4.1 人脸识别开锁（12 分）", styles["h2"]))
    s.append(tbl([
        ["验收项", "负责人", "验收操作", "通过标准"],
        ["人脸注册", "C+A", "FaceRegister 页录入", "registered_faces 有记录"],
        ["实时识别", "C+B", "视频流刷脸", "熟人绿框+姓名"],
        ["开锁", "C+E+A", "熟人刷脸", "DoorLock 变 unlocked"],
        ["拒开", "C+E+A", "陌生人刷脸", "DoorLock 变 denied"],
        ["陌生人告警", "C+E", "查告警中心", "type=FACE_UNKNOWN"],
        ["通行记录", "E+A", "AccessLog 页", "unlock/denied 有记录"],
    ], [2.5 * cm, 1.5 * cm, 4 * cm, 4.5 * cm], styles))

    s.append(Paragraph("4.2 目标检测 — 门禁区域（25 分）", styles["h2"]))
    s.append(tbl([
        ["验收项", "负责人", "验收操作", "通过标准"],
        ["区域配置", "E+A", "ZoneEditor 画框保存", "zones 表有数据"],
        ["闯入检测", "D", "未授权进入区域", "INTRUSION 告警"],
        ["过近检测", "D", "靠近边缘小于X像素", "PROXIMITY 告警"],
        ["停留检测", "D", "门前停留>X秒", "LOITER 告警"],
        ["参数可配", "E+D", "修改 zone 阈值", "无需改代码"],
    ], [2.5 * cm, 1.5 * cm, 4 * cm, 4.5 * cm], styles))

    s.append(Paragraph("4.3 视频异常检测（20 分，≥2 种）", styles["h2"]))
    s.append(tbl([
        ["验收项", "负责人", "验收操作", "通过标准"],
        ["尾随 TAILGATE", "D", "unlock 后第二人出现", "告警触发"],
        ["徘徊 LOITER", "D", "未认证停留超时", "告警触发"],
    ], [2.5 * cm, 1.5 * cm, 4 * cm, 4.5 * cm], styles))

    s.append(Paragraph("4.4 告警中心（8 分）", styles["h2"]))
    s.append(tbl([
        ["验收项", "负责人", "验收操作", "通过标准"],
        ["列表展示", "E+A", "AlertCenter 页", "分页可见所有告警"],
        ["告警处置", "E+A", "点击处置", "status→handled"],
        ["监控日志", "A+E", "GET /api/logs", "可查询历史"],
        ["事件回放", "A", "replay 页/API", "可看截图"],
    ], [2.5 * cm, 1.5 * cm, 4 * cm, 4.5 * cm], styles))

    s.append(PageBreak())

    # ── 5 API 详细 ──
    s.append(Paragraph("五、API 接口详细说明", styles["h1"]))
    s.append(tbl([
        ["接口", "方法", "负责人", "请求/响应要点"],
        ["/video_feed/{id}", "GET", "B", "MJPEG 流；无需 JSON"],
        ["/api/auth/login", "POST", "E", "入:{username,password} 出:{access_token}"],
        ["/api/face/register", "POST", "C", "入:{user_id,image(base64)} 出:{message}"],
        ["/api/door/unlock", "POST", "C+E", "入:{user_id,stream_id} 内部调用；写 access_log"],
        ["/api/door/status", "GET", "E", "出:{status:locked|unlocked|denied}"],
        ["/api/zones", "CRUD", "E", "points_json:[[x,y],...] safe_distance dwell_time"],
        ["/api/alerts", "GET", "E", "参:page,type,status 出:分页列表"],
        ["/api/alerts", "POST", "E", "内部:C/D 调用 create_alert"],
        ["/api/alerts/{id}/handle", "PUT", "E", "出:handled_at 更新"],
        ["/api/access/logs", "GET", "E", "出:通行记录列表"],
        ["/api/logs", "GET", "A", "监控日志查询"],
        ["/api/replay/{id}", "GET", "A", "出:snapshot_url, video_path"],
        ["/api/docs", "GET", "E", "Swagger UI"],
    ], [3 * cm, 1 * cm, 1 * cm, 7.5 * cm], styles))

    s.append(Spacer(1, 6))
    s.append(Paragraph("5.1 告警类型枚举", styles["h2"]))
    s.append(tbl([
        ["type 值", "含义", "触发模块", "负责人"],
        ["FACE_UNKNOWN", "陌生人", "face_service", "C"],
        ["INTRUSION", "闯入区域", "detection_service", "D"],
        ["PROXIMITY", "距边缘过近", "detection_service", "D"],
        ["LOITER", "停留超时", "detection_service", "D"],
        ["TAILGATE", "尾随进入", "detection_service", "D"],
    ], [2.5 * cm, 2 * cm, 3 * cm, 1.5 * cm], styles))

    s.append(PageBreak())

    # ── 6 日程详细 ──
    s.append(Paragraph("六、按日详细进度（7/6 — 7/15）", styles["h1"]))
    s.append(tbl([
        ["日期", "节点", "牛雨昊(A)", "苏哲勋(B)", "王梓铭(C)", "李东礼(D)", "刘帅华(E)", "刘澎潮(F)"],
        ["7/6", "启动", "Collaborators\nVue init", "租服务器\n装依赖", "Conda+dlib", "写检测方案", "config\nuser模型", "文档模板\n日报"],
        ["7/7", "环境", "路由布局\nElement Plus", "Nginx-RTMP\n推流通", "下载模型\ndemo", "方案给F\nservice框架", "zone/alert模型\nrequirements", "v1.0草稿"],
        ["7/8", "立项", "Login原型", "video.py\nMJPEG", "静态人脸demo", "—", "素材给F", "提交v1.0\n答辩"],
        ["7/9", "联调①", "Login.vue\napi封装", "多路流", "face/register", "读zones", "login API\nzones API", "日报"],
        ["7/10", "核心", "FaceRegister\nZoneEditor", "gen_frames框架", "实时识别\nunlock", "HOG检测", "alert_service\nalerts表", "日报"],
        ["7/11", "中期", "DoorMonitor\nmerge main", "联调保障", "陌生人告警", "闯入检测", "Swagger\nalerts API", "提交v2.0"],
        ["7/12", "完善", "AlertCenter\nlogs API", "Nginx反代", "—", "过近+尾随", "告警CRUD", "日报"],
        ["7/13", "部署", "build部署\nreplay", "生产环境", "AI部署", "停留检测", "MySQL部署", "v3.0草稿"],
        ["7/14", "测试", "UI走查\nGit截图", "稳定性", "准确率", "告警测试", "导出Swagger", "视频+v3.0"],
        ["7/15", "结题", "演示+打包", "推流保障", "人脸演示", "检测演示", "后端保障", "提交全部文档"],
    ], [0.9 * cm, 0.9 * cm, 1.75 * cm, 1.75 * cm, 1.75 * cm, 1.75 * cm, 1.75 * cm, 1.75 * cm], styles))

    s.append(Spacer(1, 6))
    s.append(Paragraph("6.1 里程碑检查清单", styles["h2"]))
    s.append(tbl([
        ["里程碑", "时间", "必达项", "负责人"],
        ["立项", "7/8 下午", "v1.0+推流demo+人脸静态demo+仓库链接", "F+A+B+C"],
        ["中期", "7/11 下午", "v2.0+登录+视频+人脸注册+识别+区域API", "F+全组"],
        ["结题", "7/15", "全功能部署+文档+视频+Git截图", "F+A+全组"],
    ], [2 * cm, 2 * cm, 6.5 * cm, 2 * cm], styles))

    s.append(PageBreak())

    # ── 7 依赖关系 ──
    s.append(Paragraph("七、任务依赖关系（阻塞项）", styles["h1"]))
    s.append(tbl([
        ["下游任务", "依赖上游", "说明"],
        ["A Login.vue", "E login API", "7/9 前 E 必须提供接口"],
        ["A DoorMonitor", "B video_feed + E door/status", "视频+状态接口"],
        ["A FaceRegister", "C face/register", "7/10 联调"],
        ["C 实时识别", "B gen_frames 框架", "B 7/10 前留 hook"],
        ["C unlock", "E door_service + access_log", "E 7/10 前就绪"],
        ["D 区域检测", "E zones API + B 视频帧", "区域数据+帧输入"],
        ["D 告警", "E alert_service", "统一写库"],
        ["F v1.0", "B/C/D/E 7/7 素材", "延期则文档延期"],
        ["全员部署", "B 服务器 + A deploy", "7/13 集成"],
    ], [3.5 * cm, 3.5 * cm, 5.5 * cm], styles))

    s.append(Spacer(1, 6))
    s.append(Paragraph("7.1 联调时间表", styles["h2"]))
    s.append(tbl([
        ["时间", "参与人", "内容", "地点/方式"],
        ["7/9 15:00", "A+E", "登录 API 联调", "本地/远程"],
        ["7/9 16:00", "A+B", "视频流 MJPEG 展示", "浏览器"],
        ["7/10 15:00", "A+C", "人脸注册+识别", "前后端"],
        ["7/10 16:00", "C+E", "开锁+通行记录", "API"],
        ["7/11 10:00", "全组", "中期演示彩排", "服务器"],
        ["7/12 15:00", "A+D+E", "告警+区域联调", "AlertCenter"],
        ["7/14 10:00", "全组", "结题彩排", "服务器"],
    ], [2 * cm, 2 * cm, 4.5 * cm, 3 * cm], styles))

    # ── 8 仓库结构 ──
    s.append(Paragraph("八、GitHub 仓库目录（当前+目标）", styles["h1"]))
    s.append(tbl([
        ["路径", "状态", "目标内容", "负责人"],
        ["frontend/src/views/*.vue", "⬜", "6 个页面组件", "牛雨昊"],
        ["frontend/src/api/*.js", "⬜", "6 个 API 模块", "牛雨昊"],
        ["backend/blueprints/*.py", "⬜", "11 个 Blueprint", "见第三节"],
        ["backend/services/*.py", "⬜", "4 个 Service", "C/D/E/A"],
        ["backend/models/*.py", "⬜", "4 个 Model", "刘帅华"],
        ["nginx/nginx.conf", "⬜", "RTMP+反代", "苏哲勋"],
        ["deploy/*.sh", "✅", "完善并实测", "牛雨昊"],
        ["docs/", "✅", "架构说明+分工表", "刘澎潮"],
    ], [3.5 * cm, 0.8 * cm, 4.5 * cm, 2.7 * cm], styles))

    s.append(Spacer(1, 8))
    s.append(Paragraph("九、协作规范", styles["h1"]))
    s.append(Paragraph(
        "• 9:00 晨会（牛雨昊主持）　• 17:00 向刘澎潮反馈文档素材　• PR 审查：A 审 frontend，E 审 business<br/>"
        "• 禁止直接 push main　• 阻塞超过 2 小时在群里@相关人　• 缺勤 3 次取消成绩",
        styles["body"],
    ))
    s.append(Spacer(1, 8))
    s.append(Paragraph(REPO_URL, styles["subtitle"]))
    s.append(Paragraph("牛雨昊、苏哲勋、王梓铭、李东礼、刘帅华、刘澎潮", styles["subtitle"]))
    return s


def main():
    fn = register_font()
    styles = build_styles(fn)
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    doc = SimpleDocTemplate(
        OUTPUT, pagesize=A4,
        leftMargin=1.2 * cm, rightMargin=1.2 * cm,
        topMargin=1.2 * cm, bottomMargin=1.2 * cm,
    )
    doc.build(build_story(styles))
    print(f"PDF 已生成: {OUTPUT}")


if __name__ == "__main__":
    main()
