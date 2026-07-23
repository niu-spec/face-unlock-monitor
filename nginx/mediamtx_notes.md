# MediaMTX 流媒体说明

本项目使用 MediaMTX 承接 OBS RTMP 推流，并向 Django（RTSP）与浏览器（WebRTC）分发。

> 完整端口与 Nginx 反代示例见 [README.md](./README.md)。

## 本机 OBS 推流

```text
服务器：rtmp://127.0.0.1:9090/stream
推流码：1
完整地址：rtmp://127.0.0.1:9090/stream/1
```

远端服务器时，把 `127.0.0.1` 换成你的公网 IP / 域名，并保证安全组放行 **9090/TCP**。

## 后端内部读取

Django / OpenCV 统一读取 RTSP：

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

云服务器需放行 **8889/TCP** 与 **8189/UDP**（WebRTC）。若与面板冲突，不要映射宿主机 `8888`。

启动容器时请设置 `PUBLIC_HOST`（见 `deploy/mediamtx_run.sh`），否则浏览器 WebRTC 可能拿不到正确 ICE 地址。

## 自检

- `docker ps` 中可见 `home-mediamtx`
- OBS 推流后 `docker logs home-mediamtx` 出现 `stream/1` online
- Django `/api/video/status` 可访问
- WebRTC：`http://127.0.0.1:8889/stream/1/`（或你的 `PUBLIC_HOST`）
- MJPEG 备用：`/video_feed/1`
