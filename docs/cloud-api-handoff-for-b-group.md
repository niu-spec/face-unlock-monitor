# 云服务器 Nginx 配置交接 — 发给 B 组

> 前端联调需要：WebRTC 预览走云，AI 从 RTSP 抽帧，业务 API 通过 **80 端口** 访问。

---

## 1. 联调架构

```text
OBS 推流
  -> RTMP :9090 (MediaMTX)
      ├-> WebRTC :8889 -> 浏览器低延迟预览
      └-> RTSP :8554  -> 云 Django 抽帧 + AI 检测

浏览器
  -> http://152.136.29.158/api/...   业务 API（登录、告警、人数等）
  -> http://152.136.29.158:8889/...  WebRTC 预览
```

两条链路互不阻塞：WebRTC 只负责看画面，AI 从 RTSP 抽帧，结果通过 API 返回前端。

---

## 2. 当前状态（已正常）

| 项 | 地址 | 状态 |
|----|------|------|
| MediaMTX 推流 | `rtmp://152.136.29.158:9090/stream/{id}` | ✅ |
| WebRTC 预览 | `http://152.136.29.158:8889/stream/1/` | ✅ |
| 视频 / AI 状态 | `http://152.136.29.158/api/video/status` | ✅（`has_frame: true`） |
| Admin | `http://152.136.29.158/admin/` | ✅ |
| 80 端口 | 公网可访问 | ✅ |

---

## 3. 还需要改的（Nginx 80 端口）

以下业务 API 在 80 端口返回 **404**，需要增加 Nginx 反代：

| 路径 | 用途 |
|------|------|
| `/api/auth/` | 登录 / 注册 |
| `/api/home/` | 人数统计 |
| `/api/alerts/` | 告警中心 |
| `/api/households/` | 家庭管理 |
| `/api/zones/` | 危险区域 |
| `/api/events/` | 事件记录 |
| `/api/face/` | 人脸注册 |
| `/api/docs/` | Swagger 文档 |

### 建议 Nginx 配置

若业务 API 与视频后端在同一个 Django（`8010`）上：

```nginx
# 已有（不用动）
location /api/video/ {
    proxy_pass http://127.0.0.1:8010/api/video/;
}

location /video_feed/ {
    proxy_pass http://127.0.0.1:8010/video_feed/;
    proxy_buffering off;
    proxy_cache off;
}

# 需要新增
location /api/ {
    proxy_pass http://127.0.0.1:8010/api/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

> 若业务 API 在另一个 Django 进程（如 `8000`），将 `proxy_pass` 改为对应端口。

---

## 4. 不需要做的

- ❌ 不需要对外开放 `8000` / `8010` 端口（直连返回 502，走 80 即可）
- ❌ 不需要暴露 RTSP `8554` 到公网（AI 在云内网拉流）
- ❌ 不需要前端开发者在本地安装 MediaMTX

---

## 5. 配好后的验证命令

```bash
curl http://152.136.29.158/api/auth/captcha/      # 应返回 200
curl http://152.136.29.158/api/home/presence/      # 应返回 200
curl http://152.136.29.158/api/alerts/              # 应返回 401（未登录，但不是 404）
curl http://152.136.29.158/api/video/status         # 应返回 200，workers 有 has_frame
```

---

## 6. 前端切换配置（B 组配好后由前端执行）

```env
# frontend/.env.development
VITE_API_TARGET=http://152.136.29.158
VITE_WEBRTC_BASE_URL=http://152.136.29.158:8889
VITE_VIDEO_FEED_TARGET=http://152.136.29.158
```

---

## 7. OBS 推流参数（WebRTC 低延迟）

| 配置项 | 值 |
|--------|-----|
| 服务器 | `rtmp://152.136.29.158:9090/stream` |
| 推流码 | `1`（客厅）/ `2`（厨房） |
| 编码 | H.264，**B 帧 = 0** |
| 分辨率 | 640×360，15fps |
| 关键帧间隔 | 1 秒 |

> WebRTC 不支持带 B 帧的 H.264。若黑屏，检查 OBS 是否关闭了 B 帧。

---

## 8. 相关文档

- [video-stream-webrtc-integration.md](video-stream-webrtc-integration.md) — WebRTC + MJPEG 完整对接说明
- [backend_handoff_video_stream.md](backend_handoff_video_stream.md) — B 组流媒体交接
- [DEV_SETUP.md](DEV_SETUP.md) — 本地开发环境指南
