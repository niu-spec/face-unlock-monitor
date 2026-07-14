# 部署脚本说明

> **生产服务器**：152.136.29.158  
> **项目路径**：`/service/home-camera-monitor`  
> **详细步骤**：以本目录脚本与下方说明为准；架构与端口见 [docs/总体架构说明.md](../docs/总体架构说明.md)、[nginx/README.md](../nginx/README.md)

---

## 脚本一览

| 脚本 | 用途 |
|------|------|
| `deploy-all.sh` | **主入口** — git pull、migrate、重启 backend、构建前端、MediaMTX、nginx |
| `deploy-lib.sh` | Deploy 共用 helper（`sudo -n` 封装 systemctl/nginx） |
| `jenkins.sudoers.example` | Jenkins CD 所需 sudoers 模板 |
| `start_backend.sh` | systemd 启动 gunicorn（绑定 `BACKEND_BIND`，默认 8010） |
| `mediamtx_run.sh` | Docker 重启 MediaMTX（9090/8554/8889/8189） |
| `install_jenkins.sh` | 云服务器一次性安装 Jenkins |
| `deploy-django.sh` | 旧版 fallback（:8000，无 systemd 时用） |
| `deploy-frontend.sh` | 旧版前端部署（路径硬编码，优先用 deploy-all） |

---

## 环境变量

| 变量 | 默认 | 说明 |
|------|------|------|
| `DEPLOY_PATH` | `/service/home-camera-monitor` | 项目根目录 |
| `DEPLOY_BRANCH` | `dev` | git 拉取分支 |
| `SKIP_GIT_UPDATE` | `0` | 设为 `1` 跳过 git pull |
| `DJANGO_SERVICE` | `home-camera-backend` | systemd 服务名 |
| `DEPLOY_USE_SUDO` | `auto` | `auto`/`1` 时非 root 用户通过 `sudo -n` 执行 systemctl/nginx |
| `DEPLOY_MEDIAMTX` | `0` | `1` 时才重启 `home-mediamtx`；Jenkins CD 默认 `0` |
| `NGINX_BIN` | _(auto)_ | 显式指定 nginx 路径（宝塔：`/www/server/nginx/sbin/nginx`） |
| `VIDEO_FRAME_SKIP` | `5` | AI 至少间隔多少个采集帧运行一次；推理始终取最新帧 |
| `VIDEO_CAPTURE_BUFFER_SIZE` | `1` | OpenCV RTSP 采集缓冲区大小，生产环境保持低延迟 |
| `VIDEO_JPEG_QUALITY` | `80` | MJPEG 输出质量（40～95） |
| `VIDEO_METADATA_CACHE_SECONDS` | `5` | 摄像头家庭和危险区域元数据缓存时间 |

---

## systemd 服务

`home-camera-backend.service` 安装示例：

```bash
sudo cp deploy/home-camera-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable home-camera-backend
sudo systemctl restart home-camera-backend
```

---

## 端口矩阵

| 端口 | 服务 | 说明 |
|------|------|------|
| 80 | Nginx | 对外入口 |
| 8010 | gunicorn | **视频 + AI + 业务 API**（生产推荐） |
| 8000 | gunicorn | 本地开发默认 |
| 9090 | MediaMTX | RTMP 推流 |
| 8554 | MediaMTX | RTSP（内网） |
| 8889 | MediaMTX | WebRTC |
| 8080 | Jenkins | CI/CD 控制台 |

---

## 典型部署命令

```bash
cd /service/home-camera-monitor
git fetch origin dev && git merge --ff-only origin/dev
DEPLOY_BRANCH=dev DEPLOY_MEDIAMTX=0 bash deploy/deploy-all.sh
```

仅当需要重建 MediaMTX 容器时：

```bash
DEPLOY_MEDIAMTX=1 bash deploy/deploy-all.sh
```
