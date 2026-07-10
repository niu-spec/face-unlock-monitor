# 项目文档索引

> **仓库**：https://github.com/niu-spec/home-camera-monitor  
> **主分支**：`dev`  
> **最后整理**：2026-07-10

---

## 开发入门

| 文档 | 读者 | 说明 |
|------|------|------|
| [DEV_SETUP.md](DEV_SETUP.md) | 全员 | **本地开发必读** — conda、dlib、MySQL、前后端启动 |
| [../README.md](../README.md) | 全员 | 项目概览与快速链接 |
| [../frontend/README.md](../frontend/README.md) | A/E | 前端路由、环境变量 |
| [../backend/README.md](../backend/README.md) | B/C/D/E | 后端入口，指向 DEV_SETUP |

---

## 架构与验收

| 文档 | 读者 | 说明 |
|------|------|------|
| [总体架构说明.md](总体架构说明.md) | 全员 / 答辩 | **结题设计文档** — 架构、模块、API、部署 |
| [AI危险区域与异常检测模块_技术文档.md](AI危险区域与异常检测模块_技术文档.md) | D | 检测模块技术细节 |

---

## 流媒体与云部署（B 组）

| 文档 | 读者 | 说明 |
|------|------|------|
| [B组-云部署与联调指引.md](B组-云部署与联调指引.md) | B | **统一部署手册** — pull、重启、Nginx、验收 |
| [video-stream-webrtc-integration.md](video-stream-webrtc-integration.md) | B/A | WebRTC + MJPEG + 端口/OBS 详细说明 |
| [../nginx/README.md](../nginx/README.md) | B | Nginx 反代示例（8010） |
| [../deploy/README.md](../deploy/README.md) | B/A | 部署脚本说明 |
| [B组-Jenkins安装指引.md](B组-Jenkins安装指引.md) | B | Jenkins 一次性安装 + Webhook |

---

## CI/CD 与规范

| 文档 | 读者 | 说明 |
|------|------|------|
| [CI-CD使用说明.md](CI-CD使用说明.md) | A / 全员 | Jenkins（CD）+ GitHub Actions（CI） |
| [OpenSpec使用说明.md](OpenSpec使用说明.md) | A / Cursor 用户 | OpenSpec 工作流 |
| [OpenSpec组员上手指南.md](OpenSpec组员上手指南.md) | C/D/E | 非 Cursor 组员 OpenSpec 指南 |
| [../openspec/config.yaml](../openspec/config.yaml) | Agent | 项目上下文（技术栈、流 ID、团队） |

---

## 文档维护约定

1. **不要**在文档里写死 commit hash，用「最新 `dev`」+ `git log -1`
2. **不要**再写「双推 GitLab」— 主仓库仅 GitHub
3. 流媒体细节以 `video-stream-webrtc-integration.md` 为准
4. 云部署步骤以 `B组-云部署与联调指引.md` 为准
5. 架构变更同步更新 `总体架构说明.md` 与 `openspec/config.yaml`
