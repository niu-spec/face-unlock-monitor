# 本地开发环境指南

> 修 bug / 联调前请先对照本文完成环境配置。

## 1. 前置依赖

| 工具 | 版本 | 用途 |
|------|------|------|
| [Anaconda / Miniconda](https://docs.conda.io/) | 最新 | **后端 Python 3.10 + dlib**（Windows 必须） |
| Node.js | 18+ | 前端 Vite |
| MySQL | 8.x / 9.x | 业务数据库 |
| Git | — | 代码管理 |

**不要用 `backend/venv`（Python 3.13）跑人脸识别** — dlib 在 Windows 上无法通过 pip 安装到 3.13。

## 2. 一键配置后端

```powershell
# 项目根目录
.\scripts\setup_backend.ps1
```

脚本会创建/更新 conda 环境 `home-camera`，安装 dlib + Django 依赖，并运行 `manage.py check` 与人脸模块测试。

## 3. 数据库

默认连接参数（见 `backend/config/settings.py`）：

| 变量 | 默认值 |
|------|--------|
| `DB_HOST` | `127.0.0.1` |
| `DB_PORT` | `3306` |
| `DB_USER` | `root` |
| `DB_PASSWORD` | `Root@1234` |
| `DB_NAME` | `home_camera_monitor` |

```powershell
conda activate home-camera
cd backend

# 按需设置密码（PowerShell）
$env:DB_PASSWORD = "你的密码"

python manage.py migrate
python manage.py createsuperuser          # 可选
python manage.py seed_demo_data           # 可选：填充演示家庭/告警数据
```

演示账号（`seed_demo_data` 默认）：手机号 `15333601865`，密码 `123456`。

## 4. 启动服务

**终端 1 — 后端**

```powershell
.\scripts\start_backend.ps1
# 或手动：
conda activate home-camera
cd backend
python manage.py runserver 8000
```

**终端 2 — 前端**

```powershell
.\scripts\start_frontend.ps1
# 或手动：
cd frontend
npm install
npm run dev
```

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:5173 |
| 后端 API | http://localhost:8000/api/ |
| Swagger | http://localhost:8000/api/docs/ |
| Admin | http://localhost:8000/admin/ |

前端 `/api` 与 `/video_feed` 由 Vite 代理到后端 `:8000`（见 `frontend/vite.config.js`）。监控页主预览使用 WebRTC（MediaMTX :8889），AI 标注通过 `/api/video/presence/` 获取后在 Canvas 叠加。

## 5. 环境变量

### 后端（`backend/.env.example` → 复制为 `.env` 或直接 export）

```powershell
$env:DB_PASSWORD = "Root@1234"
$env:DJANGO_DEBUG = "True"
```

### 前端（`frontend/.env.development`）

| 变量 | 默认 | 说明 |
|------|------|------|
| `VITE_API_TARGET` | `http://localhost:8000` | API 代理目标 |
| `VITE_VIDEO_FEED_TARGET` | 同 API | 视频流代理（可指向云服务器） |

当前 `.env.development` 将视频流指向云服务器，API 仍走本地 8000。

## 6. 联调约定

### 活跃家庭（多家庭隔离）

前端 Axios 自动携带请求头：

```
X-Active-Household-Id: <家庭 ID>
```

部分接口（如人脸注册 `POST /api/face/register/`）也支持 form 字段 `household_id`。须先在「家庭管理」页切换当前家庭。

### 流 ID 双轨

| 层 | 客厅 | 厨房 |
|----|------|------|
| 视频（MediaMTX） | `1` | `2` |
| 业务（zones/alerts） | `living_room` | `kitchen` |
| WebRTC 预览 | `http://{IP}:8889/stream/1/` | `.../stream/2/` |
| overlay API | `/api/video/presence/?stream_id=1` | `...stream_id=2` |
| MJPEG 备用 | `/video_feed/1` | `/video_feed/2` |

映射见 `frontend/src/constants/streams.js`。

### 人脸识别

- 代码：`backend/apps/face/`
- 依赖：conda 环境内的 dlib + face_recognition
- 模型：由 `face-recognition-models` 包提供，不提交 Git
- 验证：`python manage.py test apps.face.tests`

## 7. 常见问题

| 现象 | 原因 | 处理 |
|------|------|------|
| `face_recognition 未安装` | 用了 venv 或未 activate conda | `conda activate home-camera` |
| `请先选择当前家庭` | 未设置活跃家庭 | 前端登录后进入家庭管理并切换 |
| 前端连不上 API | 后端未启动或端口不对 | 确认 `runserver 8000` |
| MySQL 连接失败 | 密码/库名不对 | 检查 `DB_*` 环境变量，库名 `home_camera_monitor` |
| conda env update 报编码错 | yml 含中文注释 | 已改为纯 ASCII，重新 pull |

## 8. Linux 服务器部署

生产环境脚本见 `deploy/deploy-django.sh`。Linux 上 dlib 可通过 conda-forge 或系统编译依赖 + pip 安装；推荐同样使用 `environment.yml`。

流媒体：OBS → RTMP `:9090` → MediaMTX → RTSP `:8554` → Django OpenCV 拉流。详见 [nginx/README.md](../../nginx/README.md)、[video-stream-webrtc-integration.md](../部署运维/video-stream-webrtc-integration.md)。

## 9. 相关文档

- [backend/README.md](../../backend/README.md) — 后端专项说明
- [frontend/README.md](../../frontend/README.md) — 前端路由与目录
- [backend/dat/README.md](../../backend/dat/README.md) — dlib 模型
- [OpenSpec 使用说明](../项目管理/OpenSpec/OpenSpec使用说明.md) — 规范驱动开发流程
