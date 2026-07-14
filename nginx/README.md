# Nginx / MediaMTX 配置

居家摄像头视频推流服务当前使用 MediaMTX，Nginx 只负责将 Web/API 请求反代到 Django/Gunicorn。

**架构与预览链路（WebRTC + overlay）**：见 [docs/总体架构说明.md](../docs/总体架构说明.md)；端口与反代以本文为准。

## 端口一览

| 端口 | 协议 | 用途 |
|------|------|------|
| 9090 | RTMP | OBS/手机推流入站 |
| 8554 | RTSP | Django/OpenCV 内部拉流 |
| 8889 | HTTP | WebRTC 低延迟预览页面 |
| 8189 | UDP | WebRTC ICE 连接 |

- OBS 推流地址：`rtmp://{IP}:9090/stream/{stream_id}`
- WebRTC 预览：`http://{IP}:8889/stream/{stream_id}/`
- 后端 RTSP：`rtsp://127.0.0.1:8554/stream/{stream_id}`
- MJPEG 备用：`http://{IP}/video_feed/{stream_id}`
- 典型 stream_id：`1`（客厅）、`2`（厨房）

生产 Nginx 反代示例（**业务 + AI + 视频 API 均在 8010 单体后端**）：

```nginx
location /api/ {
    proxy_pass http://127.0.0.1:8010;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}

location /video_feed/ {
    proxy_pass http://127.0.0.1:8010/video_feed/;
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 3600;
}
```

> 生产环境 `home-camera-backend.service` 绑定 `127.0.0.1:8010`；本地开发 `runserver :8000`。架构与预览链路见 [总体架构说明.md](../docs/总体架构说明.md)。
