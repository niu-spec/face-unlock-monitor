# B 组流媒体交接说明（索引）

> **负责人**：B 苏哲勋  
> **完整文档**请按优先级阅读：

| 文档 | 内容 |
|------|------|
| **[B组-云部署与联调指引.md](B组-云部署与联调指引.md)** | 统一部署、Nginx、验收 |
| **[video-stream-webrtc-integration.md](video-stream-webrtc-integration.md)** | WebRTC + MJPEG + OBS + 端口 |
| **[../nginx/README.md](../nginx/README.md)** | Nginx 反代示例 |
| **[../deploy/README.md](../deploy/README.md)** | 部署脚本 |

## 快速参考

```text
OBS 推流：rtmp://152.136.29.158:9090/stream/1
RTSP 拉流：rtsp://127.0.0.1:8554/stream/1
WebRTC：http://152.136.29.158:8889/stream/1/
MJPEG：http://152.136.29.158/video_feed/1
生产 API/AI：127.0.0.1:8010（Nginx 反代 /api/）
```

AI 处理链已在 `backend/apps/video_stream/services.py` 的 `process_frame()` 中接入 face + detection，无需再单独「挂接 AI 钩子」。
