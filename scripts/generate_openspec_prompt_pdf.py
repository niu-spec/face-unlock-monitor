# -*- coding: utf-8 -*-
"""生成 OpenSpec 组员提示词使用指南 PDF（总册）"""

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
OUTPUT = os.path.join(ROOT, "docs", "项目管理", "OpenSpec", "OpenSpec组员提示词指南.pdf")
REPO_URL = "https://github.com/niu-spec/home-camera-monitor"
GUIDE_URL = f"{REPO_URL}/blob/dev/docs/项目管理/OpenSpec/OpenSpec组员上手指南.md"
FONT_PATH = r"C:\Windows\Fonts\msyh.ttc"
FONT_NAME = "MicrosoftYaHei"
DOCUMENT_DATE = date(2026, 7, 8)

TEAM = {
    "A": ("牛雨昊", "组长/前端/Git/部署"),
    "B": ("苏哲勋", "流媒体/MediaMTX/视频拉流"),
    "C": ("王梓铭", "AI人脸/人员统计"),
    "D": ("李东礼", "AI危险区域/异常检测"),
    "E": ("刘帅华", "Django业务/数据库/Swagger"),
    "F": ("刘澎潮", "专职文档"),
}

MEMBER_BRANCH = {
    "B": "feature/nginx 或 feature/django-video-stream",
    "C": "feature/face",
    "D": "feature/detection",
    "E": "feature/business",
    "F": "—（不写代码）",
}

MEMBER_SPECS = {
    "B": [
        "openspec/specs/video-stream/spec.md",
        "openspec/changes/ai-video-integration/design.md",
    ],
    "C": [
        "openspec/config.yaml",
        "openspec/changes/ai-video-integration/tasks.md（第 2 节）",
        "openspec/changes/ai-video-integration/design.md",
        "openspec/changes/ai-video-integration/specs/ai-video-integration/spec.md",
    ],
    "D": [
        "openspec/config.yaml",
        "openspec/changes/ai-video-integration/tasks.md（第 3 节）",
        "openspec/changes/ai-video-integration/design.md",
        "openspec/changes/ai-video-integration/specs/ai-video-integration/spec.md",
    ],
    "E": [
        "openspec/config.yaml",
        "openspec/specs/alerts-events/spec.md（或对应 capability）",
    ],
    "F": [
        "openspec/specs/ 下各 capability",
        "openspec/changes/archive/ 已归档 change",
    ],
}

GENERAL_PROMPT = """我在做 home-camera-monitor 项目（居家智能摄像头，Django + Vue3）。

请先阅读我提供的以下文件，理解项目约定和任务要求，不要急着写代码：

1. openspec/config.yaml
2. openspec/changes/ai-video-integration/tasks.md
3. openspec/changes/ai-video-integration/design.md
4. openspec/changes/ai-video-integration/specs/ai-video-integration/spec.md

读完后告诉我：你理解了我的哪些任务、涉及哪些文件、接口约定是什么。"""

MEMBER_PROMPTS = {
    "B": [
        (
            "修改 process_frame()（视频流）",
            """我要修改 backend/apps/video_stream/services.py 的 process_frame()。
请先读：
- openspec/specs/video-stream/spec.md
- openspec/changes/ai-video-integration/design.md

要求保留 face 和 detection 的接入扩展点，不要破坏处理器链结构。
流程：face 先处理 → detection 再处理 → 返回标注后的帧。""",
        ),
    ],
    "C": [
        (
            "任务 2.1 — 人脸检测与编码",
            """按 openspec/changes/ai-video-integration/tasks.md 的 2.1，
在 backend/apps/face/services.py 中接入 dlib 人脸检测与 128 维编码比对。

要求：
- 使用 face_recognition 库（HOG 模型）
- 编码维度必须是 128
- 与 registered_faces.json 家人库比对
- 不要改动无关文件""",
        ),
        (
            "任务 2.2 — 注册 API",
            """完成任务 2.2：实现 POST /api/face/register/ 与家人库持久化。

参考现有 backend/apps/face/views.py 和 services.py，
注册成功后同时写入数据库 FamilyMember 和 registered_faces.json。""",
        ),
        (
            "任务 2.3 + 2.4 — presence 与陌生人告警",
            """完成任务 2.3 和 2.4：
- process_frame() 处理后更新 GET /api/home/presence/ 的人数统计
- 检测到陌生人时触发 FACE_UNKNOWN 告警（调用 apps.alerts.services.create_alert）
- 告警有 30 秒冷却，避免重复触发""",
        ),
        (
            "接入视频流（最关键）",
            """按 openspec/changes/ai-video-integration/design.md 的处理器链设计，
把 backend/apps/face/services.py 接入
backend/apps/video_stream/services.py 的 process_frame()。

流程：face 先处理 → 画框标注 → 更新 presence → 返回标注后的帧。
现有 face 模块代码已有，重点是挂到视频流钩子上。""",
        ),
    ],
    "D": [
        (
            "任务 3.1 — HOG 行人检测",
            """按 tasks.md 3.1，在 backend/apps/detection/services.py 中用 HOG 行人检测
判断人员是否进入危险区域。person_boxes 为 None 时内部自动跑 HOG。""",
        ),
        (
            "任务 3.2 — 厨房禁区闯入",
            """完成任务 3.2：当 child 角色的人进入厨房禁区多边形时，
触发 INTRUSION 告警。区域配置从 apps.zones.models.Zone 读取，
forbidden_roles 包含 'child' 的区域才检测。""",
        ),
        (
            "任务 3.3 — 积水/着火/跌倒",
            """完成任务 3.3：实现积水/着火/跌倒检测，告警类型分别为 WATER、FIRE、FALL。
参考 detection/services.py 现有 HSV 检测逻辑，确保调用 create_alert 写入数据库。""",
        ),
        (
            "接入视频流",
            """按 design.md，在 process_frame() 处理器链中，face 处理完之后接 detection：
- 传入 stream_id、zones、person_boxes、face_roles
- 用 draw_overlays() 在帧上画检测框和区域多边形
- 告警类型用 INTRUSION / WATER / FIRE / FALL""",
        ),
    ],
    "E": [
        (
            "修改现有 API",
            """我要修改 [告警/区域/家庭] 相关 API。
请先读 openspec/specs/alerts-events/spec.md（或对应 spec），
确保改动符合规格里的 Scenario，不要破坏现有接口格式。""",
        ),
        (
            "新增功能",
            """我要新增 [功能名] API。
请参考 openspec/changes/archive/ 里已有 change 的格式，
帮我起草 proposal.md 和 tasks.md，我先给组长确认再写代码。""",
        ),
    ],
    "F": [
        (
            "文档对齐规格",
            """我在写项目文档，请以 openspec/specs/ 为权威来源，
帮我检查 [某功能] 的描述是否与 spec 一致。
如发现 spec 与实现不一致，请列出差异点。""",
        ),
    ],
}

FINISH_PROMPT = """任务 [X.X] 已完成，请帮我：
1. 检查是否符合 openspec/changes/ai-video-integration/specs/ 里的 Scenario
2. 列出需要勾选 tasks.md 的哪几项（把 [ ] 改成 [x]）
3. 建议的 git commit message"""


def register_font():
    pdfmetrics.registerFont(TTFont(FONT_NAME, FONT_PATH, subfontIndex=0))
    return FONT_NAME


def build_styles(fn):
    return {
        "title": ParagraphStyle(
            "title", fontName=fn, fontSize=17, leading=22, alignment=TA_CENTER,
            spaceAfter=8, textColor=colors.HexColor("#1a365d"),
        ),
        "subtitle": ParagraphStyle(
            "subtitle", fontName=fn, fontSize=9.5, leading=14, alignment=TA_CENTER,
            spaceAfter=12, textColor=colors.HexColor("#4a5568"),
        ),
        "h1": ParagraphStyle(
            "h1", fontName=fn, fontSize=13, leading=18, spaceBefore=10, spaceAfter=5,
            textColor=colors.HexColor("#2c5282"),
        ),
        "h2": ParagraphStyle(
            "h2", fontName=fn, fontSize=10.5, leading=15, spaceBefore=7, spaceAfter=4,
            textColor=colors.HexColor("#2d3748"),
        ),
        "body": ParagraphStyle("body", fontName=fn, fontSize=9, leading=13, spaceAfter=5),
        "small": ParagraphStyle(
            "small", fontName=fn, fontSize=8, leading=11,
            textColor=colors.HexColor("#4a5568"),
        ),
        "cell": ParagraphStyle("cell", fontName=fn, fontSize=7.5, leading=11),
        "cell_bold": ParagraphStyle(
            "cell_bold", fontName=fn, fontSize=7.5, leading=11,
            textColor=colors.HexColor("#1a365d"),
        ),
        "code": ParagraphStyle(
            "code", fontName=fn, fontSize=8, leading=12, spaceAfter=6,
            textColor=colors.HexColor("#1a202c"), leftIndent=10, rightIndent=10,
            backColor=colors.HexColor("#f7fafc"),
        ),
    }


def esc(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def tbl(data, widths, styles, hdr=1):
    rows = []
    for r, row in enumerate(data):
        nr = []
        for cell in row:
            st = styles["cell_bold"] if r < hdr else styles["cell"]
            txt = f"<b>{cell}</b>" if r < hdr else esc(cell)
            nr.append(Paragraph(txt.replace("\n", "<br/>"), st))
        rows.append(nr)
    t = Table(rows, colWidths=widths, repeatRows=hdr)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, hdr - 1), colors.HexColor("#ebf4ff")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def code_block(styles, text):
    return Paragraph(esc(text).replace("\n", "<br/>"), styles["code"])


def add_prompt_section(story, styles, title, prompt):
    story.append(Paragraph(title, styles["h2"]))
    story.append(code_block(styles, prompt))
    story.append(Spacer(1, 4))


def add_workflow(story, styles):
    story.append(Paragraph("一、三步上手", styles["h1"]))
    steps = [
        "1. git pull 拉最新 dev 代码，切到自己的 feature 分支",
        "2. 打开 openspec/changes/ai-video-integration/tasks.md，找到自己那节任务",
        "3. 把规格文件内容贴给 Agent，复制下方提示词，说「按 tasks X.X 实现」",
        "4. 做完勾选 tasks.md，push 到 feature 分支，PR 到 dev，Assign 牛雨昊 Review",
    ]
    for step in steps:
        story.append(Paragraph(step, styles["body"]))

    story.append(Spacer(1, 6))
    story.append(Paragraph("二、要先读的文件", styles["h1"]))
    story.append(tbl(
        [
            ["负责人", "先看这些文件"],
            ["王梓铭（C）", "tasks.md 第 2 节 + design.md + specs/"],
            ["李东礼（D）", "tasks.md 第 3 节 + design.md + specs/"],
            ["刘帅华（E）", "openspec/specs/ 下对应 capability"],
            ["苏哲勋（B）", "openspec/specs/video-stream/spec.md"],
            ["刘澎潮（F）", "openspec/specs/ 各 capability"],
        ],
        [3 * cm, 12.5 * cm],
        styles,
    ))

    story.append(Spacer(1, 6))
    story.append(Paragraph("三、Git 命令", styles["h1"]))
    story.append(code_block(styles, """git checkout dev
git pull origin dev
git checkout feature/face      # 王梓铭
# git checkout feature/detection  # 李东礼
# git checkout feature/business   # 刘帅华

git add .
git commit -m "feat(face): 完成 tasks 2.1-2.2"
git push origin feature/face"""))

    story.append(Spacer(1, 6))
    story.append(Paragraph("四、PR 描述模板", styles["h1"]))
    story.append(code_block(styles, """关联 OpenSpec: ai-video-integration
完成任务: 2.1, 2.2
规格参考: openspec/changes/ai-video-integration/specs/

测试说明:
- 本地接口可访问
- 符合 spec 中的 Scenario"""))


def build_main_story(styles):
    story = []
    story.append(Paragraph("软件工程学期实训 II", styles["title"]))
    story.append(Paragraph("OpenSpec 组员提示词使用指南", styles["title"]))
    story.append(Paragraph(
        f"home-camera-monitor　|　{DOCUMENT_DATE}<br/>"
        f"仓库：{REPO_URL}<br/>"
        f"在线文档：{GUIDE_URL}",
        styles["subtitle"],
    ))

    story.append(Paragraph("核心理解", styles["h1"]))
    story.append(Paragraph(
        "OpenSpec 不是 Cursor 专属工具，而是仓库里的 Markdown 规格文档。"
        "组员只需 git pull 拿到 openspec/ 目录，按 tasks.md 写代码，再 push 回 GitHub。"
        "任意 AI Agent（ChatGPT、Claude、Copilot 等）都能用。",
        styles["body"],
    ))

    add_workflow(story, styles)
    story.append(PageBreak())

    story.append(Paragraph("五、通用开场提示词（所有人第一次对话先发）", styles["h1"]))
    story.append(code_block(styles, GENERAL_PROMPT))
    story.append(Spacer(1, 6))

    story.append(Paragraph("六、做完后发给 Agent 的提示词", styles["h1"]))
    story.append(code_block(styles, FINISH_PROMPT))
    story.append(PageBreak())

    story.append(Paragraph("七、各角色专用提示词", styles["h1"]))
    for code in ["B", "C", "D", "E", "F"]:
        name, role = TEAM[code]
        story.append(Paragraph(f"{name}（{code}）— {role}", styles["h2"]))
        story.append(Paragraph(f"分支：{MEMBER_BRANCH[code]}", styles["small"]))
        for spec in MEMBER_SPECS[code]:
            story.append(Paragraph(f"• {spec}", styles["small"]))
        story.append(Spacer(1, 4))
        for title, prompt in MEMBER_PROMPTS[code]:
            add_prompt_section(story, styles, title, prompt)
        story.append(PageBreak())

    story.append(Paragraph("八、常见问题", styles["h1"]))
    faq = [
        ("没有 Cursor 能用吗？", "可以。OpenSpec 文件在 Git 仓库里，任何编辑器 + Agent 都能用。"),
        ("tasks 全部做完后？", "在 PR 或群里通知牛雨昊，由组长归档 change。"),
        ("spec 和代码不一致？", "在群里说明，不要擅自改 openspec/specs/ 主目录。"),
        ("要做的新功能没有 change？", "联系牛雨昊新建，或参考 archive/ 范例起草。"),
    ]
    for q, a in faq:
        story.append(Paragraph(f"Q：{q}", styles["h2"]))
        story.append(Paragraph(f"A：{a}", styles["body"]))

    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "一句话：git pull → 读 tasks.md → 贴提示词给 Agent → 勾选 tasks → PR 到 dev",
        styles["subtitle"],
    ))
    return story


def build_member_story(styles, code):
    name, role = TEAM[code]
    story = []
    story.append(Paragraph("软件工程学期实训 II", styles["title"]))
    story.append(Paragraph(f"OpenSpec 提示词 — {name}", styles["title"]))
    story.append(Paragraph(
        f"代号 {code}　|　{role}　|　{DOCUMENT_DATE}<br/>"
        f"分支：{MEMBER_BRANCH[code]}　|　{REPO_URL}",
        styles["subtitle"],
    ))

    story.append(Paragraph("一、你的工作流", styles["h1"]))
    for step in [
        "git checkout dev && git pull origin dev",
        f"git checkout {MEMBER_BRANCH[code].split('或')[0].strip() if '或' in MEMBER_BRANCH[code] else MEMBER_BRANCH[code]}",
        "打开 tasks.md 找到自己那节任务",
        "把下方提示词复制给 Agent，附上规格文件内容",
        "做完勾选 tasks.md，push 并 PR 到 dev",
    ]:
        story.append(Paragraph(f"• {step}", styles["body"]))

    story.append(Spacer(1, 6))
    story.append(Paragraph("二、要先读的文件", styles["h1"]))
    for spec in MEMBER_SPECS[code]:
        story.append(Paragraph(f"• {spec}", styles["body"]))

    story.append(Spacer(1, 6))
    story.append(Paragraph("三、通用开场提示词", styles["h1"]))
    story.append(code_block(styles, GENERAL_PROMPT))

    story.append(Spacer(1, 6))
    story.append(Paragraph("四、你的专用提示词（复制使用）", styles["h1"]))
    for title, prompt in MEMBER_PROMPTS[code]:
        add_prompt_section(story, styles, title, prompt)

    story.append(Spacer(1, 6))
    story.append(Paragraph("五、做完后提示词", styles["h1"]))
    story.append(code_block(styles, FINISH_PROMPT))

    story.append(Spacer(1, 6))
    story.append(Paragraph("六、提交命令", styles["h1"]))
    branch = MEMBER_BRANCH[code].split("或")[0].strip() if "或" in MEMBER_BRANCH[code] else MEMBER_BRANCH[code]
    if branch != "—（不写代码）":
        story.append(code_block(styles, f"""git add .
git commit -m "feat({code.lower()}): 完成 tasks X.X"
git push origin {branch}"""))

    story.append(Spacer(1, 8))
    story.append(Paragraph(GUIDE_URL, styles["subtitle"]))
    return story


def write_pdf(path, story):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    doc = SimpleDocTemplate(
        path, pagesize=A4,
        leftMargin=1.2 * cm, rightMargin=1.2 * cm,
        topMargin=1.2 * cm, bottomMargin=1.2 * cm,
    )
    doc.build(story)


def main():
    fn = register_font()
    styles = build_styles(fn)

    write_pdf(OUTPUT, build_main_story(styles))
    print(f"总册 PDF 已生成: {OUTPUT}")


if __name__ == "__main__":
    main()
