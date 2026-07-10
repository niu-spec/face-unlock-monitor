# B 组云部署与联调指引

> **负责人**：B 苏哲勋（流媒体 / Nginx / 云服务器）  
> **服务器**：152.136.29.158  
> **代码仓库**：https://github.com/niu-spec/home-camera-monitor（分支 `dev`）  
> **最后更新**：2026-07-10

本文档合并了此前的「下一步部署」「WebRTC 人脸叠加」「AI 联调待办」等内容，作为 **唯一** 的云上操作手册。

---

## 1. 生产环境拓扑

```
浏览器 :80
  ├── 前端静态资源（frontend/dist）
  ├── /api/*        → Django 视频/AI 后端 :8010（推荐）
  └── /video_feed/* → Django 视频/AI 后端 :8010

OBS/摄像头 → RTMP :9090 → MediaMTX → RTSP :8554 → OpenCV 拉流
浏览器 WebRTC 预览 → :8889

Jenkins CD（可选）→ deploy/deploy-all.sh
GitHub Actions CI → push 自动 test/build
```

| 组件 | 地址 / 端口 | 说明 |
|------|-------------|------|
| 项目目录 | `/service/home-camera-monitor` | monorepo |
| 视频/AI 后端 | `127.0.0.1:8010` | systemd `home-camera-backend` |
| 业务 API（若另有进程） | `:8000` | 勿与 8010 混用路由 |
| MediaMTX RTMP | `:9090` | OBS 推流 |
| MediaMTX RTSP | `:8554` | 内网，Django 拉流 |
| MediaMTX WebRTC | `:8889` | 低延迟预览 |
| Jenkins | `:8080` | CI/CD（见 Jenkins 安装指引） |

---

## 2. 拉取最新代码

> Git 历史若被重写，用 `reset --hard`，不要用普通 `pull`。

```bash
cd /service/home-camera-monitor
git fetch origin dev
git reset --hard origin/dev
git log -1 --oneline    # 确认已是最新 dev
```

---

## 3. 部署（CD）

### 方式 A：脚本一键部署（推荐）

```bash
cd /service/home-camera-monitor
DEPLOY_BRANCH=dev bash deploy/deploy-all.sh
```

脚本会：migrate → 重启 backend → `npm ci && build` → 重启 MediaMTX → reload nginx。

### 方式 B：Jenkins 手动 Deploy

CI 通过后，在 Jenkins Pipeline 的 **Deploy Production** 阶段点 **Deploy**。  
详见 [B组-Jenkins安装指引.md](B组-Jenkins安装指引.md)。

### 方式 C：分步手动（排错时用）

```bash
cd /service/home-camera-monitor/backend
source venv/bin/activate          # 或 conda activate home-camera
pip install -r requirements.txt -q
python manage.py migrate --noinput
python manage.py check
sudo systemctl restart home-camera-backend

cd ../frontend
npm ci && npm run build

bash ../deploy/mediamtx_run.sh
sudo nginx -t && sudo systemctl reload nginx
```

---

## 4. Nginx 路由要点

**`/api/` 与 `/video_feed/` 必须指向视频/AI 后端（8010）**，否则会出现「有画面但人数为 0、无 AI 框」。

参考配置见 [../nginx/home-camera-monitor.conf.example](../nginx/home-camera-monitor.conf.example) 与 [../nginx/README.md](../nginx/README.md)。

关键片段：

```nginx
location /api/ {
    proxy_pass http://127.0.0.1:8010;
}
location /video_feed/ {
    proxy_pass http://127.0.0.1:8010;
}
```

---

## 5. 验收清单

部署完成后执行：

```bash
# 视频 worker 状态（应有 presence、frame_size）
curl -s http://127.0.0.1:8010/api/video/status | python3 -m json.tool

# 人数 API
curl -s http://127.0.0.1/api/home/presence/ -H "Authorization: Bearer <token>"

# 服务状态
systemctl status home-camera-backend --no-pager
docker ps | grep mediamtx
```

| 检查项 | 通过标准 |
|--------|----------|
| OBS 推流 | RTMP :9090 有流 |
| WebRTC | `http://IP:8889/stream/1/` 有画面 |
| MJPEG | `/video_feed/1` 有画面 |
| AI 画框 | MJPEG 或 WebRTC+Canvas 可见红/绿人脸框 |
| 人数 | `/api/home/presence/` 或 `/api/video/status` 的 `presence.total > 0`（有人时） |
| 告警 | 陌生人/闯入等能在告警中心看到 |

前端验收：登录 → 监控页 → WebRTC 模式 + MJPEG 备用模式各测一遍。

---

## 6. 常见问题

### 人数一直为 0

1. 确认 Nginx `/api/` 指向 **8010** 而非 8000  
2. 确认 `git log -1` 为最新 dev  
3. `journalctl -u home-camera-backend -n 50` 看 AI 处理链是否报错  
4. `curl http://127.0.0.1:8010/api/video/status` 看 `last_processed_error`

### 无 AI 画框

1. 云上需安装 dlib：`pip show dlib face_recognition`  
2. 确认 `process_frame()` 无异常（见 status API）  
3. WebRTC 模式依赖前端 Canvas 叠加 + `presence.frame_size`

### deploy-all.sh 报 working tree has local changes

```bash
git status
git stash   # 或 git reset --hard origin/dev
```

### MediaMTX / WebRTC 无画面

确认 Docker 容器映射了 8889/8189（见 `deploy/mediamtx_run.sh`）。

---

## 7. 相关文档

| 文档 | 用途 |
|------|------|
| [video-stream-webrtc-integration.md](video-stream-webrtc-integration.md) | 流媒体详细配置 |
| [B组-Jenkins安装指引.md](B组-Jenkins安装指引.md) | Jenkins + Webhook |
| [CI-CD使用说明.md](CI-CD使用说明.md) | 组员日常 CI 用法 |
| [../deploy/README.md](../deploy/README.md) | 部署脚本说明 |

---

## 8. 完成后反馈 A 组

```
1. git log -1 输出
2. curl /api/video/status 关键字段
3. 前端截图（WebRTC + 人脸框 / 人数统计）
4. Jenkins 构建号（若已装）
```
