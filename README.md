# home-camera-monitor

Smart home camera monitoring system with RTMP streaming, Django business backend, and dlib face recognition — family identification, person counting, stranger alerts, danger zones, and emergency detection.

## 应用场景

**居家智能摄像头监控**：通过家庭摄像头实时分析家中画面，识别家庭成员、统计当前在家人数、检测陌生人；支持设定危险区域（如厨房禁止小孩进入）；对积水、着火、人员摔倒等异常情况进行识别并告警。

## 核心功能

| 模块 | 功能 |
|------|------|
| 人脸识别 | 家庭成员注册与识别、陌生人告警 |
| 人员统计 | 实时统计画面/家中人数、熟人/陌生人数量 |
| 危险区域 | 前端画框配置禁区（如厨房），小孩进入即告警 |
| 异常检测 | 积水、着火、人员摔倒（≥2 种，满足课程验收） |
| 告警中心 | 事件展示、处置、日志与回放 |

## 技术栈

| 层次 | 技术 |
|------|------|
| 前端 | Vue3 + Vite + Element Plus + Vue Router + Axios |
| 业务后端 | Django 4.2 + DRF + SimpleJWT + Swagger（:8000） |
| AI 模块 | OpenCV + dlib + face_recognition（Django apps 内集成） |
| 数据库 | MySQL（`home_camera_monitor`） |
| 流媒体 | OBS → RTMP(:9090) → MediaMTX → RTSP → Django MJPEG |
| 部署 | gunicorn + Nginx 反代 |

## 项目结构

```
home-camera-monitor/
├── frontend/          # Vue3 前端 (:5173)
├── backend/           # Django 后端 (:8000)
├── nginx/             # MediaMTX / Nginx 反代说明
├── deploy/            # 部署脚本
├── docs/              # 项目文档（含 DEV_SETUP.md）
└── scripts/           # setup / start / 工具脚本
```

## 快速开始

完整步骤见 **[docs/DEV_SETUP.md](docs/DEV_SETUP.md)**。

### 1. 后端（conda + Python 3.10 + dlib）

```powershell
.\scripts\setup_backend.ps1      # 首次：创建 conda 环境 home-camera
.\scripts\start_backend.ps1        # 启动 Django :8000
```

### 2. 前端

```powershell
.\scripts\start_frontend.ps1       # 启动 Vite :5173
```

### 3. 数据库（首次）

```powershell
conda activate home-camera
cd backend
$env:DB_PASSWORD = "your_password"
python manage.py migrate
python manage.py seed_demo_data    # 可选演示数据
```

| 地址 | URL |
|------|-----|
| 前端 | http://localhost:5173 |
| Swagger | http://localhost:8000/api/docs/ |
| Admin | http://localhost:8000/admin/ |

### 推流与预览

```
推流：rtmp://{服务器IP}:9090/stream/1
预览：http://localhost:5173 → /video_feed/1（Vite 代理）
```

详见 [nginx/README.md](nginx/README.md)。

## 文档

- [本地开发环境指南](docs/DEV_SETUP.md) — **修 bug 前必读**
- [backend_handoff_video_stream.md](docs/backend_handoff_video_stream.md) — 流媒体交接（B 组）
- [video-stream-webrtc-integration.md](docs/video-stream-webrtc-integration.md) — WebRTC 低延迟预览 + MJPEG 备用配置
- [frontend/README.md](frontend/README.md) — 前端路由
- [总体架构说明](docs/总体架构说明.md)
- [OpenSpec 使用说明](docs/OpenSpec使用说明.md)
- [CI/CD 使用说明](docs/CI-CD使用说明.md) — Jenkins + GitHub Actions

## 团队

见 [CONTRIBUTORS.md](CONTRIBUTORS.md)

## License

MIT
