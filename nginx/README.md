# Nginx / MediaMTX 配置

Nginx 负责 Web / API 反代；**推拉流由 MediaMTX 承担**（不经过 Nginx-RTMP）。

```text
OBS / 手机  --RTMP:9090-->  MediaMTX  --RTSP:8554-->  Django OpenCV（AI）
                              |
                              +--WebRTC:8889-->  浏览器 iframe（低延迟预览）
浏览器  --:80-->  Nginx  --/api,/video_feed-->  gunicorn :8010
                 Nginx  --静态-->  frontend/dist
```

## 端口

| 端口 | 协议 | 用途 | 是否建议对外 |
|------|------|------|-------------|
| 80 | HTTP | Nginx：前端 + API + MJPEG 备用 | 是 |
| 8010 | HTTP | gunicorn（仅本机） | 否（只给 Nginx） |
| 9090 | RTMP | OBS / 手机推流 | 是（推流端需要） |
| 8554 | RTSP | Django 内网拉流 | 否（本机即可） |
| 8889 | HTTP | MediaMTX WebRTC 预览页 | 是（或见下方反代） |
| 8189 | UDP | WebRTC ICE | 是 |

## 推拉流地址（把 `{HOST}` 换成公网 IP 或域名）

| 角色 | 地址 |
|------|------|
| OBS 推流服务器 | `rtmp://{HOST}:9090/stream` |
| 推流码 / stream_id | `1`（客厅）、`2`（厨房） |
| 完整推流 URL | `rtmp://{HOST}:9090/stream/1` |
| 后端拉流（服务器本机） | `rtsp://127.0.0.1:8554/stream/1` |
| 浏览器 WebRTC | `http://{HOST}:8889/stream/1/` |
| MJPEG 备用（经 Nginx） | `http://{HOST}/video_feed/1` |

启动 MediaMTX 时必须设置与 `{HOST}` 一致的 `PUBLIC_HOST`，否则浏览器 WebRTC ICE 可能失败：

```bash
PUBLIC_HOST=your.example.com bash deploy/mediamtx_run.sh
```

## Nginx 示例

完整可复制文件：[home-camera-monitor.conf.example](./home-camera-monitor.conf.example)

要点：

1. `root` 指向前端构建产物（默认 `/service/home-camera-monitor/frontend/dist`）
2. `/api/`、`/admin/`、`/video_feed/` 反代到 `127.0.0.1:8010`
3. `/static/` 指向 Django `collectstatic` 目录（Swagger / Admin）
4. WebRTC **默认直连** MediaMTX `:8889`（前端 `VITE_WEBRTC_BASE_URL`）；若只想开放 80 端口，可用示例里的 `/webrtc/` 反代，并把前端构建变量改成同源路径

## 前端生产构建

构建前设置（会打进静态资源）：

```bash
# frontend/.env.production
VITE_WEBRTC_BASE_URL=http://your.example.com:8889
# 若使用 Nginx /webrtc/ 反代，可改为：
# VITE_WEBRTC_BASE_URL=https://your.example.com/webrtc
```

本地开发见 [frontend/.env.development.example](../frontend/.env.development.example)。

## 后端生产环境

```bash
cp backend/.env.example backend/.env.production
# 至少设置：DB_*、DJANGO_SECRET_KEY、DJANGO_DEBUG=False
# RTSP_BASE_URL=rtsp://127.0.0.1:8554/stream
# RTMP_PUBLIC_BASE_URL=rtmp://your.example.com:9090/stream
```

systemd 示例见 [deploy/home-camera-backend.service](../deploy/home-camera-backend.service)。

## 云安全组建议放行

- `80/TCP`（或 `443`）
- `9090/TCP`（推流）
- `8889/TCP` + `8189/UDP`（WebRTC；若已用 `/webrtc/` 反代且 ICE 仍走 8189，UDP 仍需放行）

## 相关文档

- [mediamtx_notes.md](./mediamtx_notes.md) — MediaMTX 补充说明
- [deploy/README.md](../deploy/README.md) — 一键部署脚本
- [docs/开发指南/DEV_SETUP.md](../docs/开发指南/DEV_SETUP.md) — 本地启动
