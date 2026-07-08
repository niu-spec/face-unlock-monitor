# OpenSpec 使用说明

> **项目**：home-camera-monitor  
> **负责人**：A 牛雨昊（初始化与维护）  
> **仓库路径**：`openspec/`、`.cursor/commands/`

---

## 1. 什么是 OpenSpec

OpenSpec 是规范驱动开发（SDD）工具，核心流程：

```
/opsx-propose  →  写 proposal / design / specs / tasks
/opsx-apply    →  按 tasks 实现代码
/opsx-archive  →  归档 change，合并 specs 到主目录
```

**目的**：先对齐「做什么」，再写代码，减少前后端/AI 模块接口不一致。

---

## 2. 目录结构

```
openspec/
├── config.yaml              # 项目上下文（技术栈、流 ID、团队分工）
├── specs/                   # 当前系统规格（真相来源）
│   ├── video-stream/
│   ├── zone-management/
│   ├── auth-accounts/
│   ├── home-monitor/
│   ├── alerts-events/
│   ├── frontend-integration/
│   └── ai-video-integration/   # C/D 待实现
└── changes/
    ├── ai-video-integration/   # 进行中的 change（C/D 使用）
    └── archive/                # 已归档 change
```

---

## 3. Cursor 命令

在 Cursor 聊天框输入（不是终端）：

| 命令 | 用途 |
|------|------|
| `/opsx-propose <名称>` | 新建 change，生成 4 个制品 |
| `/opsx-apply <名称>` | 按 tasks.md 实现并勾选 |
| `/opsx-archive <名称>` | 归档并合并 specs |
| `/opsx-explore` | 纯讨论，不写代码 |
| `/opsx-sync <名称>` | 仅同步 specs，不归档 |

---

## 4. 已完成的 change 记录

| Change | 日期 | 说明 | 关联 commit |
|--------|------|------|-------------|
| `bootstrap-from-docs` | 2026-07-08 | 从架构文档提炼 6 个 capability spec | f55be66 |
| `frontend-zone-stream-alignment` | 2026-07-08 | 流 ID 对齐 + ZoneEditor Canvas | 57a0cc1 |
| `user-manage-page` | 2026-07-08 | 用户管理聚合页 `/users` | 见 dev 最新 commit |

---

## 5. 进行中的 change（组员使用）

### `ai-video-integration` — C/D 负责

- **C 王梓铭**：tasks 2.x 人脸识别、presence、陌生人告警
- **D 李东礼**：tasks 3.x 区域闯入、积水/着火/跌倒

使用方式：

1. 在 Cursor 输入 `/opsx-apply ai-video-integration`
2. 按 tasks.md 逐项实现
3. 完成后 `/opsx-archive ai-video-integration`

规格详见：`openspec/changes/ai-video-integration/specs/`

---

## 6. 各成员如何开始新功能

以 E 新增 API 为例：

```
/opsx-propose alert-filter-api
```

AI 会生成 proposal → design → specs → tasks，审核后：

```
/opsx-apply alert-filter-api
/opsx-archive alert-filter-api
```

**约定**：每个 feature PR 尽量关联一个 OpenSpec change。

---

## 7. 答辩演示建议

1. 打开 `openspec/specs/` 展示 7 个 capability
2. 打开 `openspec/changes/archive/` 展示完整 propose → archive 记录
3. 演示 `/opsx-propose` 创建一个小 change（可选）
4. 说明 ZoneEditor、UserManage 等功能均有 spec 可追溯

---

## 8. 本地 CLI（可选）

```powershell
npm install -g @fission-ai/openspec@latest
cd 项目根目录
openspec list                    # 查看 active changes
openspec status --change <名>    # 查看制品进度
openspec validate <名>             # 校验 change
openspec archive <名> -y           # 归档
```

---

*文档维护：变更 OpenSpec 流程时请同步更新本文档。*
