# 后端视频流与数据库对接说明

## 1. 当前部署概况

```text
公网 IP：152.136.29.158
域名：suzhexun.site
服务器环境：宝塔 Linux 面板
主项目：mini-rednote
视频流模块：home-camera-monitor
```

当前后端拆分为两个本地服务：

```text
mini-rednote 主业务后端：127.0.0.1:8000
home-camera-monitor 视频流后端：127.0.0.1:8010
MediaMTX 流媒体服务：9090 / 8554
Docker MySQL 8.0：127.0.0.1:3307
```

Nginx 公网入口约定：

```text
/api/video/   -> 127.0.0.1:8010
/video_feed/  -> 127.0.0.1:8010
/api/         -> 127.0.0.1:8000
/admin/       -> 127.0.0.1:8000
```

## 2. 视频流链路

```text
OBS / 摄像头
  -> RTMP: rtmp://152.136.29.158:9090/stream/1
  -> MediaMTX
  -> RTSP: rtsp://127.0.0.1:8554/stream/1
  -> Django / OpenCV 视频后端
  -> MJPEG: http://152.136.29.158/video_feed/1
```

OBS 配置：

```text
服务：自定义
服务器：rtmp://152.136.29.158:9090/stream
推流码：1
```

## 3. 多摄像头约定

后续统一使用 `stream_id` 区分摄像头：

```text
摄像头 1：rtmp://152.136.29.158:9090/stream/1 -> rtsp://127.0.0.1:8554/stream/1 -> /video_feed/1
摄像头 2：rtmp://152.136.29.158:9090/stream/2 -> rtsp://127.0.0.1:8554/stream/2 -> /video_feed/2
摄像头 3：rtmp://152.136.29.158:9090/stream/3 -> rtsp://127.0.0.1:8554/stream/3 -> /video_feed/3
```

前端只使用 MJPEG：

```html
<img src="/video_feed/1" />
```

浏览器不要直接使用 RTSP。

## 4. 视频 API

```text
GET http://152.136.29.158/api/video/status
GET http://152.136.29.158/api/video/streams/1/source
GET http://152.136.29.158/video_feed/1
```

服务器本机检查：

```bash
curl -i http://127.0.0.1:8010/api/video/status
curl -i http://127.0.0.1:8010/api/video/streams/1/source
```

## 5. 数据库配置

项目数据库使用 Docker MySQL 8.0：

```text
Host: 127.0.0.1
Port: 3307
Database: home_camera_monitor
User: homecam
```

数据库密码禁止写入 GitHub、README、PR 描述、`.env.example`、截图或代码注释。服务器本地保存位置：

```text
/root/home_camera_monitor_db.env
```

systemd 通过环境文件读取：

```text
DB_NAME=home_camera_monitor
DB_USER=homecam
DB_PASSWORD=******
DB_HOST=127.0.0.1
DB_PORT=3307
```

## 6. systemd 服务

```bash
systemctl status home-mediamtx-ensure.service --no-pager
systemctl status home-camera-backend.service --no-pager
systemctl is-enabled home-mediamtx-ensure.service
systemctl is-enabled home-camera-backend.service
```

视频后端绑定端口：

```text
BACKEND_BIND=127.0.0.1:8010
```

注意：`8000` 是 mini-rednote 主业务后端，`8010` 是 home-camera-monitor 视频流后端，不要再让视频流后端绑定 `8000`。

## 7. Nginx 反代

视频路径转发到 `8010`：

```nginx
location ^~ /api/video/ {
    proxy_pass http://127.0.0.1:8010/api/video/;
    proxy_http_version 1.1;
    proxy_buffering off;
    proxy_cache off;
    proxy_request_buffering off;
    proxy_read_timeout 3600s;
    proxy_send_timeout 3600s;
}

location ^~ /video_feed/ {
    proxy_pass http://127.0.0.1:8010/video_feed/;
    proxy_http_version 1.1;
    proxy_buffering off;
    proxy_cache off;
    proxy_request_buffering off;
    gzip off;
    proxy_read_timeout 3600s;
    proxy_send_timeout 3600s;
    add_header X-Accel-Buffering "no" always;
}
```

主业务路径仍转发到 `8000`。

## 8. 验证命令

```bash
ss -lntp | grep -E "8000|8010|9090|8554|3307"
curl -i http://127.0.0.1:8010/api/video/status
curl -i http://127.0.0.1:8010/api/video/streams/1/source
curl --max-time 5 http://152.136.29.158/video_feed/1 -o /tmp/public_feed.mjpg
docker logs --tail=80 home-mediamtx | grep -E "publish|reading|stream/1|no stream|404"
```
