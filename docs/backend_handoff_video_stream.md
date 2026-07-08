# B 组流媒体与 Django 视频流交接说明

负责人：B 苏哲勋

当前可用链路：

```text
OBS 摄像头
  -> RTMP 推流
  -> MediaMTX
  -> RTSP
  -> Django / OpenCV
  -> /video_feed/1
```

## 1. 当前方案

原任务表中的 Nginx-RTMP 方案已在实测中替换为 MediaMTX。对外 OBS 推流方式保持简单：

```text
服务器：rtmp://152.136.29.158:9090/stream
推流码：1
完整地址：rtmp://152.136.29.158:9090/stream/1
```

后端统一读取服务器内部 RTSP：

```text
rtsp://127.0.0.1:8554/stream/1
```

当前 `/video_feed/1` 可播放摄像头画面，浏览器预览延迟约 5 秒。当前 `apps/video_stream/services.py` 仍是 OpenCV 拉 RTSP 版本，暂不切换为 FFmpeg 子进程 raw frame 版。

## 2. OBS 配置

直播配置：

```text
服务：自定义
服务器：rtmp://152.136.29.158:9090/stream
推流码：1
```

视频源建议只保留：

```text
视频采集设备 -> Integrated Camera
```

建议参数：

```text
分辨率：640x480 或 1280x720
FPS：15 或 20
编码器：H.264
码率：800 - 1200 Kbps
关键帧间隔：1 或 2 秒
```

## 3. MediaMTX 启动

推荐脚本：

```bash
bash deploy/mediamtx_run.sh
```

脚本启动容器：

```text
容器名：home-mediamtx
镜像：bluenviron/mediamtx:latest
9090 -> 1935 RTMP
8554 -> 8554 RTSP
```

注意：不要映射宿主机 `8888`，因为宝塔面板占用该端口。

## 4. 后端接口

健康检查：

```text
GET /api/health
```

视频状态：

```text
GET /api/video/status
```

视频源检查：

```text
GET /api/video/streams/1/source
```

MJPEG 预览：

```text
GET /video_feed/1
```

前端可直接使用：

```html
<img src="/video_feed/1" />
```

浏览器不要直接访问 RTSP 地址，生产环境由 Nginx 将 `/video_feed/` 和 `/api/video/` 反代到视频流 Django/Gunicorn，例如 `127.0.0.1:8010`。`127.0.0.1:8000` 保留给 mini-rednote 主业务后端。

## 5. C/D/E/A 联调方式

A 前端：

- 使用 `/video_feed/1` 做视频预览。
- 使用 `/api/video/status` 查看后端视频状态。
- Vite 代理需要包含 `/api` 和 `/video_feed`。

C 人脸识别：

- 不要从浏览器截图做人脸识别。
- 直接接入 `backend/apps/video_stream/services.py` 中的 OpenCV frame。
- frame 是 BGR 格式 `numpy.ndarray`。
- 在 `process_frame(frame, stream_id)` 位置接入人脸处理。

D 区域/异常检测：

- 使用同一个 frame 做检测，不要重复拉流。
- detection_service 可在 `process_frame(frame, stream_id)` 中接入。
- 事件统一交给 E 的告警服务写库。

E 业务/数据库：

- 后续开锁、通行记录和告警写入由 E 的 service/API 提供。
- B 只保留视频帧和事件 hook，不重写 E 的 models/auth/alerts/zones。

F 文档：

- 记录方案由 Nginx-RTMP 调整为 MediaMTX。
- 记录当前已完成 OBS 摄像头推流、MediaMTX 转发、Django 预览。
- 记录当前延迟约 5 秒，后续优化方向是 FFmpeg latest_frame、WebRTC 或异步 AI 线程。

## 6. 常用排查命令

检查容器：

```bash
docker ps | grep home-mediamtx
```

查看日志：

```bash
docker logs --tail=80 home-mediamtx
```

检查端口：

```bash
ss -lntp | grep -E "9090|8554"
```

RTSP 读取检查：

```bash
ffmpeg -rtsp_transport tcp -i rtsp://127.0.0.1:8554/stream/1 -t 3 -f null -
```

Django 状态检查：

```bash
curl http://127.0.0.1:8010/api/video/status
curl http://127.0.0.1:8010/api/video/streams/1/source
```

公网检查：

```text
http://152.136.29.158/api/health
http://152.136.29.158/api/video/status
http://152.136.29.158/video_feed/1
```
