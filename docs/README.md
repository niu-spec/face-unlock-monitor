# 项目文档索引

> **仓库**：https://github.com/niu-spec/home-camera-monitor  
> **主分支**：`dev`  
> **最后整理**：2026-07-11

---

## 目录结构

```
docs/
├── 课程要求/          # 课程下发的 PDF（立项/中期/结题依据）
├── 开发指南/          # 本地开发环境
├── 架构设计/          # 结题架构与模块技术文档
├── 部署运维/          # 云部署、流媒体、CI/CD
│   └── 记录/          # 部署过程沟通与问题记录
└── 项目管理/          # 分工表、OpenSpec 指南
    └── OpenSpec/
```

---

## 开发入门

| 文档 | 读者 | 说明 |
|------|------|------|
| [开发指南/DEV_SETUP.md](开发指南/DEV_SETUP.md) | 全员 | **本地开发必读** — conda、dlib、MySQL、前后端启动 |
| [../README.md](../README.md) | 全员 | 项目概览与快速链接 |
| [../frontend/README.md](../frontend/README.md) | A/E | 前端路由、环境变量 |
| [../backend/README.md](../backend/README.md) | B/C/D/E | 后端入口，指向 DEV_SETUP |

---

## 架构与验收

| 文档 | 读者 | 说明 |
|------|------|------|
| [架构设计/总体架构说明.md](架构设计/总体架构说明.md) | 全员 / 答辩 | **结题设计文档** — 架构、模块、API、部署 |
| [架构设计/AI危险区域与异常检测模块_技术文档.md](架构设计/AI危险区域与异常检测模块_技术文档.md) | D | 检测模块技术细节 |
| [架构设计/C组-反欺骗完善清单.md](架构设计/C组-反欺骗完善清单.md) | C | 活体反欺骗验收清单 |

---

## 流媒体与云部署（B 组）

| 文档 | 读者 | 说明 |
|------|------|------|
| [部署运维/B组-云部署与联调指引.md](部署运维/B组-云部署与联调指引.md) | B | **统一部署手册** — pull、重启、Nginx、验收 |
| [部署运维/video-stream-webrtc-integration.md](部署运维/video-stream-webrtc-integration.md) | B/A | WebRTC + MJPEG + 端口/OBS 详细说明 |
| [../nginx/README.md](../nginx/README.md) | B | Nginx 反代示例（8010） |
| [../deploy/README.md](../deploy/README.md) | B/A | 部署脚本说明 |
| [部署运维/B组-Jenkins安装指引.md](部署运维/B组-Jenkins安装指引.md) | B | Jenkins 一次性安装 + Webhook |

---

## CI/CD 与规范

| 文档 | 读者 | 说明 |
|------|------|------|
| [部署运维/CI-CD使用说明.md](部署运维/CI-CD使用说明.md) | A / 全员 | Jenkins（CD）+ GitHub Actions（CI） |
| [项目管理/OpenSpec/OpenSpec使用说明.md](项目管理/OpenSpec/OpenSpec使用说明.md) | A / Cursor 用户 | OpenSpec 工作流 |
| [项目管理/OpenSpec/OpenSpec组员上手指南.md](项目管理/OpenSpec/OpenSpec组员上手指南.md) | C/D/E | 非 Cursor 组员 OpenSpec 指南 |
| [../openspec/config.yaml](../openspec/config.yaml) | Agent | 项目上下文（技术栈、流 ID、团队） |

---

## 课程要求与项目管理

| 文档 | 读者 | 说明 |
|------|------|------|
| [课程要求/4_小学期任务清单.pdf](课程要求/4_小学期任务清单.pdf) | 全员 | 验收任务清单 |
| [项目管理/项目任务分工表.pdf](项目管理/项目任务分工表.pdf) | 全员 | 六组分工与进度（v1.5） |

---

## 部署过程记录

| 文档 | 说明 |
|------|------|
| [部署运维/记录/B组-CD落地任务清单.md](部署运维/记录/B组-CD落地任务清单.md) | B 组 CD 落地步骤 |
| [部署运维/记录/B组-CD落地反馈.md](部署运维/记录/B组-CD落地反馈.md) | B 组反馈与阻塞项 |
| [部署运维/记录/A组回复-B组CD阻塞修复.md](部署运维/记录/A组回复-B组CD阻塞修复.md) | A 组修复说明 |
| [部署运维/记录/生产目录文件策略.md](部署运维/记录/生产目录文件策略.md) | 生产机 .env / 数据文件策略 |

---

## 文档维护约定

1. **不要**在文档里写死 commit hash，用「最新 `dev`」+ `git log -1`
2. **不要**再写「双推 GitLab」— 主仓库仅 GitHub
3. 流媒体细节以 `部署运维/video-stream-webrtc-integration.md` 为准
4. 云部署步骤以 `部署运维/B组-云部署与联调指引.md` 为准
5. 架构变更同步更新 `架构设计/总体架构说明.md` 与 `openspec/config.yaml`
6. 课程 PDF 统一放在 `课程要求/`，不要在 `docs/` 根目录重复存放
