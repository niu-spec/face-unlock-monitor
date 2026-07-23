# 本地开发环境指南

克隆仓库后按本文配置，即可在本机运行前后端。流媒体（MediaMTX / OBS）为可选能力。

## 1. 前置依赖

| 工具 | 版本 | 用途 |
|------|------|------|
| [Anaconda / Miniconda](https://docs.conda.io/) | 最新 | **后端 Python 3.10 + dlib**（Windows 强烈推荐） |
| Node.js | 18+ | 前端 Vite |
| MySQL | 8.x / 9.x | 业务数据库 |
| Git | — | 代码管理 |
| Docker（可选） | — | 运行 MediaMTX |

> Windows 上请勿用 Python 3.13 的 `venv` 安装 dlib；请使用 conda 环境 `home-camera`。

## 2. 复制配置文件

```powershell
# 项目根目录
cp backend/.env.example backend/.env
cp frontend/.env.development.example frontend/.env.development
```

编辑 `backend/.env`，至少设置与本机一致的 `DB_PASSWORD`。

前端默认将 API 与 WebRTC 指向本机：

| 变量 | 默认 | 说明 |
|------|------|------|
| `VITE_API_TARGET` | `http://localhost:8000` | Vite 代理 `/api` |
| `VITE_WEBRTC_BASE_URL` | `http://127.0.0.1:8889` | MediaMTX WebRTC 预览 |
| `VITE_VIDEO_FEED_TARGET` | （可选） | MJPEG 备用；不设则与 API 同源 |

## 3. 一键配置后端

```powershell
.\scripts\setup_backend.ps1
```

脚本会创建/更新 conda 环境 `home-camera`，安装 dlib 与 Django 依赖，并做基础检查。

## 4. 数据库

默认连接参数见 `backend/.env.example` / `backend/config/settings.py`：

| 变量 | 默认值 |
|------|--------|
| `DB_HOST` | `127.0.0.1` |
| `DB_PORT` | `3306` |
| `DB_USER` | `root` |
| `DB_PASSWORD` | `changeme` |
| `DB_NAME` | `home_camera_monitor` |

```powershell
conda activate home-camera
cd backend

# 可选：当前 shell 临时覆盖
$env:DB_PASSWORD = "你的密码"

python manage.py migrate
python manage.py createsuperuser          # 可选
python manage.py seed_demo_data           # 可选：演示家庭 / 告警
```

演示账号（`seed_demo_data` 默认）：手机号 `13800138000`，密码 `123456`。

## 5. 启动服务

**终端 1 — 后端**

```powershell
.\scripts\start_backend.ps1
```

**终端 2 — 前端**

```powershell
.\scripts\start_frontend.ps1
```

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:5173 |
| 后端 API | http://localhost:8000/api/ |
| Swagger | http://localhost:8000/api/docs/ |
| Admin | http://localhost:8000/admin/ |

前端 `/api` 与 `/video_feed` 由 Vite 代理到后端 `:8000`。监控页主预览使用 WebRTC（MediaMTX `:8889`），AI 标注通过 `/api/video/presence/` 拉取后在 Canvas 叠加。

## 6. 流媒体（可选）

```bash
docker compose up -d
# 或 Windows：.\scripts\start_mediamtx.ps1
```

无摄像头 / 无 MediaMTX 时，登录、家庭、告警、日报等业务接口仍可使用。

推流示例（本机 MediaMTX）：

```text
OBS 服务器：rtmp://127.0.0.1:9090/stream
推流码：1
WebRTC 预览：http://127.0.0.1:8889/stream/1/
```

详见 [nginx/README.md](../../nginx/README.md)。

## 7. 开发约定

### 活跃家庭

前端 Axios 自动携带：

```text
X-Active-Household-Id: <家庭 ID>
```

须先在「家庭管理」中切换当前家庭。

### 流 ID

| 层 | 客厅 | 厨房 |
|----|------|------|
| 视频（MediaMTX） | `1` | `2` |
| 业务（zones / alerts） | `living_room` | `kitchen` |

映射见 `frontend/src/constants/streams.js`。

### 人脸识别

- 代码：`backend/apps/face/`
- 依赖：conda 环境中的 dlib + face_recognition
- 验证：`python manage.py test apps.face.tests`

## 8. 常见问题

| 现象 | 处理 |
|------|------|
| `face_recognition 未安装` | `conda activate home-camera` 后再启动后端 |
| `请先选择当前家庭` | 登录后进入家庭管理并切换 |
| 前端连不上 API | 确认后端 `runserver 8000`，检查 `VITE_API_TARGET` |
| MySQL 连接失败 | 检查 `backend/.env` 中 `DB_*`，并确认已建库 |
| WebRTC 黑屏 | 本机未起 MediaMTX 或未推流；可先只用业务功能 |

## 9. 生产部署

见 [deploy/README.md](../../deploy/README.md)。

## 10. 相关文档

- [backend/README.md](../../backend/README.md)
- [frontend/README.md](../../frontend/README.md)
- [backend/dat/README.md](../../backend/dat/README.md)
- [nginx/README.md](../../nginx/README.md)
