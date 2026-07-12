# home-camera-monitor

Smart home camera monitoring system with RTMP streaming, Django business backend, and dlib face recognition — family identification, person counting, stranger alerts, danger zones, and emergency detection.

## 应用场景

**居家智能摄像头监控**：通过家庭摄像头实时分析家中画面，识别家庭成员、统计当前在家人数、检测陌生人；支持设定危险区域（如厨房禁止小孩进入）；对积水、着火、人员摔倒等异常情况进行识别并告警。

## 核心功能

| 模块 | 功能 |
|------|------|
| 人脸识别 | 家庭成员注册与识别、陌生人告警、本机摄像头录入 |
| 人员统计 | 实时统计画面/家中人数、熟人/陌生人数量 |
| 危险区域 | 前端画框配置禁区，闯入 / 接近 / 逗留告警 |
| 异常检测 | 积水、着火、人员摔倒（≥2 种，满足课程验收） |
| 告警中心 | 事件展示、处置、日志与快照回放 |
| AI 日报 | 按日汇总告警与事件（模板 / 可选 LLM） |

## 技术栈

| 层次 | 技术 |
|------|------|
| 前端 | Vue3 + Vite + Element Plus + Vue Router + Axios |
| 后端 | Django 4.2 + DRF + SimpleJWT + Swagger |
| AI | OpenCV + dlib + face_recognition + YOLOv8n（HOG 降级） |
| 数据库 | MySQL（`home_camera_monitor`） |
| 流媒体 | OBS → RTMP(:9090) → MediaMTX → RTSP → Django AI 链；浏览器主预览 WebRTC(:8889) + Canvas overlay；MJPEG(/video_feed) 为后端备用 |
| CI/CD | GitHub Actions（CI）+ Jenkins（CD，云服务器） |
| 部署 | gunicorn(:8010) + Nginx 反代 |

## 项目结构

```
home-camera-monitor/
├── frontend/          # Vue3 前端 (:5173 本地)
├── backend/           # Django 后端 (:8000 本地 / :8010 生产)
├── nginx/             # Nginx / MediaMTX 说明
├── deploy/            # 部署脚本（见 deploy/README.md）
├── docs/              # 文档索引（见 docs/README.md）
├── openspec/          # OpenSpec 规格
├── scripts/           # 本地 setup / CI 脚本
├── Jenkinsfile        # Jenkins Pipeline
└── .github/workflows/ # GitHub Actions
```

## 快速开始

完整步骤见 **[docs/开发指南/DEV_SETUP.md](docs/开发指南/DEV_SETUP.md)**。

```powershell
.\scripts\setup_backend.ps1      # 首次：conda 环境
.\scripts\start_backend.ps1      # Django :8000
.\scripts\start_frontend.ps1     # Vite :5173
```

| 地址 | URL |
|------|-----|
| 前端 | http://localhost:5173 |
| 监控预览 | WebRTC iframe + `/api/video/presence/` overlay（见 DEV_SETUP） |
| Swagger | http://localhost:8000/api/docs/ |

推流：`rtmp://{IP}:9090/stream/1` — 详见 [nginx/README.md](nginx/README.md)

## 文档

完整索引见 **[docs/README.md](docs/README.md)**。

| 文档 | 说明 |
|------|------|
| [开发指南/DEV_SETUP.md](docs/开发指南/DEV_SETUP.md) | 本地开发（必读） |
| [架构设计/总体架构说明.md](docs/架构设计/总体架构说明.md) | 结题架构文档 |
| [部署运维/B组-云部署与联调指引.md](docs/部署运维/B组-云部署与联调指引.md) | 云服务器部署 |
| [部署运维/CI-CD使用说明.md](docs/部署运维/CI-CD使用说明.md) | Jenkins + GitHub Actions |
| [部署运维/video-stream-webrtc-integration.md](docs/部署运维/video-stream-webrtc-integration.md) | 流媒体详细配置 |
| [项目管理/OpenSpec/OpenSpec使用说明.md](docs/项目管理/OpenSpec/OpenSpec使用说明.md) | 规格驱动开发 |

## 团队

见 [CONTRIBUTORS.md](CONTRIBUTORS.md)

## License

MIT
