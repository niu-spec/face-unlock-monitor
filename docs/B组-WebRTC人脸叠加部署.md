# B 组 WebRTC 人脸叠加部署指引

> **发给**：B 苏哲勋（流媒体 / Nginx / 云服务器）  
> **日期**：2026-07-10  
> **背景**：A 组已实现 **方案 A**——在 WebRTC（MediaMTX）低延迟预览上，通过前端 Canvas 叠加 AI 人脸框；同时优化 MJPEG 画框与标签。代码已 push 到 **GitHub `dev`**，请 B 组拉取并部署。

---

## 1. 本次更新内容（commit `c1ca749`）

| 改动 | 文件 | 说明 |
|------|------|------|
| WebRTC Canvas 叠加 | `frontend/src/components/FaceOverlay.vue` | 轮询 `/api/video/status`，在 WebRTC iframe 上画人脸框 |
| 监控页集成 | `frontend/src/views/HomeMonitor.vue` | WebRTC 模式默认显示 AI 标注 |
| 坐标缩放 | `backend/apps/face/services.py` | `presence` 新增 `frame_size: { width, height }` |
| 中文人脸标签 | `backend/apps/face/services.py` | 显示 `张三 (成人)` / `陌生人`，不再显示 member_id |
| 隐藏调试 HUD | `backend/apps/video_stream/services.py` | MJPEG 左上角 `stream N` / `faces:N` 默认不显示 |
| 减少框重叠 | `backend/apps/video_stream/services.py` | 已检测到人脸时不再画黄色人体框 |
| 去掉重复文字 | `backend/apps/detection/services.py` | 移除 `persons: N` 调试行 |

**仓库（请从 GitHub 拉）**：

```text
https://github.com/niu-spec/home-camera-monitor
分支：dev
```

> 本次 A 组仅 push 了 GitHub，未 push GitLab。请使用 `git pull origin dev`。

---

## 2. 架构说明（部署前必读）

```text
OBS → MediaMTX ──→ WebRTC :8889  → 浏览器（原始画面）
              └──→ RTSP :8554 → Django AI → presence API
                                    ↓
              前端 Canvas 读取 presence.faces[].box → 叠在 WebRTC 上
```

- **WebRTC 画面本身不含画框**（MediaMTX 原始流），框由**前端 Canvas** 绘制。
- **后端必须部署**：`presence` 里要有 `frame_size`，否则框位置可能不准。
- **前端必须重新 build**：否则看不到 `FaceOverlay` 组件。
- **不需要改 MediaMTX 配置**，也**不要随便重启** `home-mediamtx`（会断 OBS 推流）。

---

## 3. 部署步骤

SSH 登录云服务器 `152.136.29.158` 后执行：

### 3.1 拉代码

```bash
cd /service/home-camera-monitor   # 按实际路径调整

git fetch origin dev
git pull origin dev

git log -1 --oneline
# 期望：c1ca749 feat(monitor): overlay face boxes on WebRTC preview via Canvas
```

### 3.2 部署后端（8010 视频服务）

```bash
cd /service/home-camera-monitor/backend
source venv/bin/activate
pip install -r requirements.txt -q
python manage.py check

systemctl restart home-camera-backend
systemctl status home-camera-backend --no-pager
```

### 3.3 部署前端

若前端与后端在同一仓库：

```bash
cd /service/home-camera-monitor/frontend
npm ci
npm run build
```

若使用独立目录（如 `/service/frontend`），先同步代码再 build，确保 `dist/` 被 Nginx 托管。

```bash
nginx -t && nginx -s reload
```

> 生产环境前端需配置 WebRTC 地址，例如 `VITE_WEBRTC_BASE_URL=http://152.136.29.158:8889`（见 `frontend/.env.development.example`）。

---

## 4. 部署后自测（服务器上）

### 4.1 API 检查

```bash
# 视频后端直连
curl -s http://127.0.0.1:8010/api/video/status | python3 -m json.tool

# 经 Nginx（前端实际路径）
curl -s http://127.0.0.1/api/video/status | python3 -m json.tool
```

**通过标准**（OBS 推流且画面中有人脸时）：

| 字段 | 期望 |
|------|------|
| `presence.updated_at` | 非 null |
| `presence.stream_id` | 与当前推流码一致（如 `"2"`） |
| `presence.total` | ≥ 1 |
| `presence.frame_size.width` | > 0（如 1920） |
| `presence.frame_size.height` | > 0（如 1080） |
| `presence.faces[0].box` | 含 `left/top/right/bottom` |
| `workers.<stream_id>.has_frame` | `true` |
| `workers.<stream_id>.last_error` | null |

### 4.2 流媒体检查（无需改动，确认仍正常即可）

```bash
docker ps | grep home-mediamtx
curl -sI http://127.0.0.1:8889/stream/2/ | head -5
```

---

## 5. 前端验收（部署完成后通知 A 组）

A 组在本地或浏览器访问监控页验证。

### 操作步骤

1. 打开监控页（本地 `http://localhost:5173/monitor` 或云上站点）
2. OBS 推流到对应摄像头（例如推流码 `2` → 厨房）
3. 选择 **WebRTC** 模式（默认）
4. 对着摄像头露脸

### 期望现象

| 项目 | 正常表现 |
|------|----------|
| WebRTC 画面 | 低延迟、有画面 |
| 人脸框 | 绿框（家人）或红框（陌生人），叠在 WebRTC 画面上 |
| 标签 | `张三 (成人)` 或 `陌生人` |
| 右侧人数 | 总人数 ≥ 1 |
| MJPEG 备用模式 | 仍有服务端画框；左上角**无**调试 HUD（除非设 `VIDEO_SHOW_HUD=true`） |

### 已知现象（非故障）

- 框与画面可能有 **0.5～1 秒** 偏差（AI 抽帧 + 前端轮询间隔）。
- 「新窗口打开 WebRTC」单独窗口**没有** Canvas 叠加（仅嵌入监控页有）。

---

## 6. Nginx 配置核对

若 WebRTC 有框但**人数仍为 0**，或 `/api/video/status` 无 `presence`，检查 Nginx 是否把 API 指到了错误进程。

**建议**：`/api/` 与 `/video_feed/` 统一反代到 **8010**（视频 + AI 同进程）：

```nginx
location /video_feed/ {
    proxy_pass http://127.0.0.1:8010/video_feed/;
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 3600;
}

location /api/ {
    proxy_pass http://127.0.0.1:8010/api/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

改完后：

```bash
nginx -t && nginx -s reload
```

WebRTC 预览 `:8889` 由 MediaMTX 直接提供，**不经过 Nginx**，保持现有端口映射即可。

---

## 7. 常见问题排查

```bash
# AI / 人脸处理日志
journalctl -u home-camera-backend -n 80 --no-pager | grep -iE "AI|face|失败|error"

# dlib 环境
source /service/home-camera-monitor/backend/venv/bin/activate
python -c "import dlib, face_recognition; print('OK')"
```

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| WebRTC 有画面但无框 | 前端未重新 build | 执行 `npm run build` 并 reload Nginx |
| WebRTC 有画面但无框 | `presence.faces` 为空 | 确认推流码与页面选中摄像头一致；对着摄像头试 |
| 有框但位置偏移 | 后端未更新，`frame_size` 缺失 | 确认 `git log` 为 `c1ca749` 并重启 8010 |
| `presence.total` 为 0 | AI 未跑或 Nginx 路由错误 | 查 journalctl；见第 6 节 |
| MJPEG 有框、WebRTC 无框 | 仅前端未部署 | 重新 build 前端 |
| `git pull` 后 commit 不对 | 拉错远程或分支 | 使用 `git pull origin dev` |

### 可选：开启 MJPEG 调试 HUD

仅在排查 AI 时需要：

```bash
# 在 home-camera-backend 的 systemd 环境或 .env 中
VIDEO_SHOW_HUD=true
```

然后 `systemctl restart home-camera-backend`。MJPEG 左上角会显示 `stream N` 与 `faces:N persons:N`。

---

## 8. 不需要做的

- ❌ 不需要 push / 同步 GitLab（本次代码在 GitHub）
- ❌ 不需要修改 MediaMTX Docker 配置
- ❌ 不需要重启 `home-mediamtx`（除非流媒体本身异常）
- ❌ 不需要对外开放 `8000` / `8010` / `8554`
- ❌ 不需要新建分支（代码在 `dev`）

---

## 9. 完成后请回复 A 组

请反馈以下信息：

1. `git log -1 --oneline` 的输出  
2. `curl -s http://127.0.0.1/api/video/status` 中是否含 `frame_size`  
3. 有人脸时 `presence.total` 的值  
4. WebRTC 模式下是否能看到 Canvas 人脸框  

**联系人**：A 牛雨昊（前端 / 联调）

**相关文档**：

- [video-stream-webrtc-integration.md](video-stream-webrtc-integration.md) — WebRTC + MJPEG 双通道架构  
- [B组-AI联调待办.md](B组-AI联调待办.md) — AI 联调背景与排查  
- [cloud-api-handoff-for-b-group.md](cloud-api-handoff-for-b-group.md) — 端口与 API 交接
