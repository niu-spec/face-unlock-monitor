# MediaMTX 流媒体说明

原任务表写的是 Nginx-RTMP，但实测中为降低排障成本并提升后端 RTSP 读取稳定性，流媒体服务替换为 MediaMTX。

> **完整配置（WebRTC + MJPEG）**：见 [README.md](./README.md)（本目录）与 [docs/总体架构说明.md](../docs/总体架构说明.md)。

## 对外 OBS 推流

OBS 仍使用 RTMP：

```text
服务器：rtmp://152.136.29.158:9090/stream
推流码：1
完整地址：rtmp://152.136.29.158:9090/stream/1
```

## 后端内部读取

Django/OpenCV 统一读取 RTSP：

```text
rtsp://127.0.0.1:8554/stream/1
```

## 端口

```text
9090 -> MediaMTX RTMP 1935
8554 -> MediaMTX RTSP 8554
8889 -> MediaMTX WebRTC HTTP 预览
8189 -> MediaMTX WebRTC ICE (UDP)
```

腾讯云安全组与宝塔需放行 **8889/TCP** 和 **8189/UDP**（WebRTC 低延迟预览）。

不要映射宿主机 `8888`，避免和宝塔面板冲突。

## 验收点

- `docker ps` 中可见 `home-mediamtx`
- OBS 推流后 `docker logs home-mediamtx` 出现 `stream/1` online
- Django `/api/video/status` 可访问
- WebRTC 预览：`http://152.136.29.158:8889/stream/1/` 低延迟有画面
- MJPEG 备用：`/video_feed/1` 可看到摄像头画面（延迟较高）
