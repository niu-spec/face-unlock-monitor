# home-camera-monitor

居家智能摄像头监控系统：RTMP/WebRTC 流媒体 + Django 业务后端 + 人脸识别与异常检测。

按下方步骤即可在本地跑起来（Windows 推荐 conda；流媒体可选）。

## 功能

| 模块 | 说明 |
|------|------|
| 人脸识别 | 家庭成员注册与识别、陌生人告警、本机摄像头录入 |
| 人员统计 | 实时统计画面人数、熟人 / 陌生人 |
| 危险区域 | 前端画框配置禁区，闯入 / 接近 / 逗留告警 |
| 异常检测 | 着火、摔倒、异常声响（可选音视频联动） |
| 告警中心 | 事件展示、处置、快照 / 短视频回放 |
| AI 日报 | 按日汇总告警与事件（规则模板；可选接入 LLM） |
| 通知 | 钉钉机器人推送与逐级升级（可选） |

## 技术栈

| 层次 | 技术 |
|------|------|
| 前端 | Vue 3 + Vite + Element Plus + Vue Router + Axios |
| 后端 | Django 4.2 + DRF + SimpleJWT + Swagger |
| AI | OpenCV + dlib / face_recognition + YOLOv8n（可降级 HOG） |
| 数据库 | MySQL 8+（库名默认 `home_camera_monitor`） |
| 流媒体 | OBS → RTMP → MediaMTX → RTSP（AI）/ WebRTC（浏览器预览） |
| CI/CD | GitHub Actions；可选 Jenkins |

## 仓库结构

```
home-camera-monitor/
├── frontend/          # Vue3 前端 (:5173)
├── backend/           # Django 后端 (:8000 本地)
├── nginx/             # Nginx / MediaMTX 说明与示例配置
├── deploy/            # 云服务器部署脚本
├── docs/              # 本地开发指南
├── scripts/           # 本地 setup / 启动 / CI 辅助脚本
├── docker-compose.yml # 可选：一键启动 MediaMTX
├── Jenkinsfile        # 可选 CD Pipeline
└── .github/workflows/ # GitHub Actions CI
```

## 快速开始

完整说明见 **[docs/开发指南/DEV_SETUP.md](docs/开发指南/DEV_SETUP.md)**。

### 1. 克隆并准备配置

```bash
git clone https://github.com/niu-spec/home-camera-monitor.git
cd home-camera-monitor

cp backend/.env.example backend/.env
cp frontend/.env.development.example frontend/.env.development
# 按本机 MySQL 密码修改 backend/.env 中的 DB_PASSWORD
```

### 2. 数据库

创建空库 `home_camera_monitor`，账号密码与 `.env` 一致。

### 3. 后端

**Windows：**

```powershell
.\scripts\setup_backend.ps1      # 首次：conda 环境 + 依赖（会自动复制 .env）
conda activate home-camera
cd backend
python manage.py migrate
cd ..
.\scripts\start_backend.ps1      # runserver :8000
```

**Linux / macOS：**

```bash
cd backend
conda env create -f environment.yml
conda activate home-camera
cp -n .env.example .env          # 编辑 DB_PASSWORD
python manage.py migrate
python manage.py runserver 8000
```

可选：`python manage.py seed_demo_data`（默认账号 `13800138000` / `123456`）。

### 4. 前端

```powershell
.\scripts\start_frontend.ps1
# 或：cd frontend && npm install && npm run dev
```

### 5. 流媒体（可选）

```bash
docker compose up -d
# Windows 也可：.\scripts\start_mediamtx.ps1
```

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:5173 |
| API / Swagger | http://localhost:8000/api/docs/ |
| Admin | http://localhost:8000/admin/ |
| WebRTC | http://127.0.0.1:8889/stream/1/ |

无 MediaMTX 时，登录、家庭、告警、日报等业务仍可用。推流 / 反代见 [nginx/README.md](nginx/README.md)。

## 配置要点

| 文件 | 作用 |
|------|------|
| `backend/.env.example` | 本地数据库、Django、钉钉、日报 AI |
| `backend/.env.production.example` | 生产环境 |
| `frontend/.env.development.example` | 本地 API / WebRTC |
| `frontend/.env.production.example` | 生产构建时的 WebRTC 地址 |
| `docker-compose.yml` | MediaMTX |
| `nginx/home-camera-monitor.conf.example` | Nginx 反代 |
| `deploy/README.md` | 云部署变量 |

## 文档

| 文档 | 说明 |
|------|------|
| [开发指南](docs/开发指南/DEV_SETUP.md) | 本地环境与启动 |
| [backend/README.md](backend/README.md) | 后端专项 |
| [frontend/README.md](frontend/README.md) | 前端路由与目录 |
| [nginx/README.md](nginx/README.md) | MediaMTX 推拉流 + Nginx 反代 |
| [deploy/README.md](deploy/README.md) | 云部署 |

## 团队

见 [CONTRIBUTORS.md](CONTRIBUTORS.md)。

## License

[MIT](LICENSE)
