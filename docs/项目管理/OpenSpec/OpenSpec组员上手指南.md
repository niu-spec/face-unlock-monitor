# OpenSpec 组员上手指南

> **项目**：home-camera-monitor  
> **适用对象**：不使用 Cursor 的组员（任意 AI Agent + GitHub）  
> **维护人**：A 牛雨昊  
> **相关文档**：[OpenSpec使用说明.md](OpenSpec使用说明.md)（含 Cursor 命令与 CLI）

---

## 1. 核心理解

OpenSpec **不是 Cursor 专属工具**，而是仓库里的一套 Markdown 规格文档：

```
openspec/
├── config.yaml              # 项目约定（技术栈、分工、流 ID）
├── specs/                   # 当前系统规格（「真相来源」）
└── changes/
    ├── ai-video-integration/   # 进行中的任务
    │   ├── tasks.md            # ← 最重要：任务清单
    │   ├── proposal.md         # 为什么做、改什么
    │   ├── design.md           # 技术方案
    │   └── specs/              # 需求规格（含 Scenario）
    └── archive/                # 已完成的 change 记录
```

**组员只需 `git pull` 拿到这些文件，按 `tasks.md` 写代码，再 push 回 GitHub。**

Cursor 里的 `/opsx-propose`、`/opsx-apply` 等命令只是其中一种操作方式；**读 Markdown + Git 提交** 同样有效。

---

## 2. 标准工作流

### 步骤 1：拉最新代码

```bash
git checkout dev
git pull origin dev
git checkout -b feature/face    # 按自己的分支命名，如 feature/detection
```

### 步骤 2：找到自己要做的规格

| 负责人 | 先看这些文件 |
|--------|-------------|
| 王梓铭（C） | `openspec/changes/ai-video-integration/tasks.md` 第 2 节 |
| 李东礼（D） | 同上，第 3 节 |
| 刘帅华（E） | `openspec/specs/` 下对应 capability |
| 苏哲勋（B） | `openspec/specs/video-stream/spec.md` |
| 刘澎潮（F） | `openspec/specs/` 各 capability，用于文档对齐 |

接口细节还在：

- `openspec/changes/ai-video-integration/design.md`
- `openspec/changes/ai-video-integration/specs/`

项目全局约定见：`openspec/config.yaml`

### 步骤 3：把规格喂给自己的 Agent

无论使用 Copilot、ChatGPT、Claude 还是其他 Agent，**开场先提供上下文**：

```
我在做 home-camera-monitor 项目的人脸识别模块。
请先阅读以下规格，再帮我写代码：

1. openspec/config.yaml（项目约定）
2. openspec/changes/ai-video-integration/tasks.md 第 2 节
3. openspec/changes/ai-video-integration/design.md
4. openspec/changes/ai-video-integration/specs/ai-video-integration/spec.md

我的任务是完成 tasks 2.1：接入 dlib 人脸检测与 128 维编码比对。
相关代码在 backend/apps/face/。
```

Agent 不需要懂 OpenSpec 命令，**读 Markdown 即可开发**。

### 步骤 4：按 tasks 写代码并勾选

对照 `tasks.md` 逐项实现。做完一项，把 `- [ ]` 改成 `- [x]`，与代码一起提交。

示例（C 组当前任务）：

```markdown
## 2. C — 人脸识别（王梓铭）
- [ ] 2.1 接入 dlib 人脸检测与 128 维编码比对
- [ ] 2.2 实现 `/api/face/register/` 与家人库持久化
- [ ] 2.3 更新 `/api/home/presence/` 人数统计
- [ ] 2.4 陌生人触发 `FACE_UNKNOWN` 告警
```

### 步骤 5：提交并提 PR

```bash
git add backend/apps/face/ openspec/changes/ai-video-integration/tasks.md
git commit -m "feat(face): 完成 tasks 2.1-2.2 人脸检测与注册 API"
git push origin feature/face
```

PR 描述模板：

```markdown
## 关联 OpenSpec
- Change: ai-video-integration
- 完成任务: 2.1, 2.2
- 规格参考: openspec/changes/ai-video-integration/specs/

## 测试说明
- [ ] 本地接口可访问
- [ ] 符合 spec 中的 Scenario
```

- **Base 分支**：`dev`
- **Review**：Assign 牛雨昊

---

## 3. 三种使用深度（按需选择）

### 方式 A：最简（推荐大多数组员）

不装任何额外工具，只读仓库里的 Markdown：

1. 打开 `tasks.md` 看任务
2. 打开 `design.md` / `specs/` 看接口约定
3. 让 Agent 读这些文件后写代码
4. 做完勾选 `tasks.md`，push 到 GitHub

### 方式 B：安装 OpenSpec CLI（可选）

有 Node.js 时可在终端查看进度：

```bash
npm install -g @fission-ai/openspec@latest
cd 项目根目录

openspec list                                    # 查看进行中的 change
openspec status --change ai-video-integration    # 查看任务进度
openspec validate ai-video-integration           # 校验规格格式
```

CLI 仅作辅助查看，**不是必须的**。

### 方式 C：开发全新功能时新建 change

例如刘帅华要加新 API：

1. 在群里请牛雨昊用 Cursor 执行 `/opsx-propose <名称>` 建好 change，组员 `git pull` 后直接用；或
2. 参考 `openspec/changes/archive/` 里已有 change 的格式，手动创建 `proposal.md`、`design.md`、`specs/`、`tasks.md`

---

## 4. 各角色实操示例

### 王梓铭（C）— 人脸识别

1. `git pull` → 读 `tasks.md` 2.x
2. 告诉 Agent：按 `openspec/changes/ai-video-integration/` 规格，将 `backend/apps/face/services.py` 接入 `backend/apps/video_stream/services.py` 的 `process_frame()`
3. 本地测试 `/api/face/register/`、`/api/home/presence/`
4. 勾选 tasks 2.1–2.4 → push → PR 到 `dev`

### 李东礼（D）— 异常检测

1. 读 `tasks.md` 3.x + `backend/apps/detection/services.py` 现有代码
2. 让 Agent 把 detection 模块挂到 `process_frame()` 处理器链
3. 测试 `INTRUSION` / `WATER` / `FIRE` / `FALL` 告警
4. 勾选 tasks → push → PR

### 刘帅华（E）— 业务 API

1. 先看 `openspec/specs/alerts-events/spec.md` 等现有规格
2. 新功能：找牛雨昊建 change，或仿 `archive/` 格式自建
3. 按 tasks 实现 → PR 注明关联 change

### 苏哲勋（B）— 视频流

1. 读 `openspec/specs/video-stream/spec.md`
2. 改 `process_frame()` 时对照 `ai-video-integration` 的 `design.md`
3. 保留 face / detection 的接入扩展点

### 刘澎潮（F）— 文档

1. 以 `openspec/specs/` 为权威来源写/更新文档
2. 发现 spec 与实现不一致时，在群里同步，由对应负责人或牛雨昊更新 change

---

## 5. 与 Git 分支的配合

```
main              ← 结题演示（仅牛雨昊合并）
dev               ← 集成分支（PR 目标）
feature/face      ← 王梓铭
feature/detection ← 李东礼
feature/business  ← 刘帅华
feature/frontend  ← 牛雨昊
```

**团队约定：**

- 每个 feature PR 关联一个 OpenSpec change
- PR 中写明完成了哪些 tasks
- `tasks.md` 勾选状态随代码一起提交
- 全部完成后，由牛雨昊归档 change（合并 specs 到 `openspec/specs/`，移至 `archive/`）

---

## 6. 给 Agent 的通用 Prompt 模板

复制以下内容，按自己的角色和任务修改后发给 Agent：

```
项目：home-camera-monitor（居家智能摄像头）
技术栈：Django 4.2 + Vue3 + OpenCV + dlib

请先阅读仓库中以下文件作为开发规范：
- openspec/config.yaml
- openspec/changes/ai-video-integration/tasks.md
- openspec/changes/ai-video-integration/design.md
- openspec/changes/ai-video-integration/specs/

我的角色：[C/D/E/B]
我的任务：完成 tasks [X.X]
代码目录：backend/apps/[face|detection|...]/

要求：
1. 严格按 spec 里的接口约定实现
2. 告警类型使用 dev 分支命名（FACE_UNKNOWN / INTRUSION / WATER / FIRE / FALL）
3. 流 ID 业务层使用 living_room / kitchen；视频层使用 1 / 2
4. API 路径保留尾部斜杠 /
5. 完成后告诉我需要勾选 tasks.md 的哪几项
```

---

## 7. 常见问题

### Q：我没有 Cursor，能参与 OpenSpec 吗？

可以。OpenSpec 文件在 Git 仓库里，任何编辑器 + 任意 Agent 都能用。

### Q：tasks 全部做完后怎么办？

在 PR 或群里通知牛雨昊，由组长执行归档（`openspec archive` 或 `/opsx-archive`），将规格合并进 `openspec/specs/`。

### Q：发现 spec 和实际代码不一致？

先在 PR / 群里说明，不要擅自改 `openspec/specs/` 主目录；通过 change 流程更新规格。

### Q：我要做的新功能没有对应 change？

联系牛雨昊新建 change，或参考 `openspec/changes/archive/` 里的范例自行起草，PR 前请组长确认。

---

## 8. 当前进行中的 change

### `ai-video-integration`（C/D 负责）

| 节 | 负责人 | 内容 |
|----|--------|------|
| 2.x | 王梓铭 | 人脸识别、presence、陌生人告警 |
| 3.x | 李东礼 | 区域闯入、积水/着火/跌倒 |
| 4.x | 全员 | OBS 推流联调、告警中心验证 |

规格路径：`openspec/changes/ai-video-integration/`

---

*文档维护：流程变更时请同步更新本文档与 [OpenSpec使用说明.md](OpenSpec使用说明.md)。*
