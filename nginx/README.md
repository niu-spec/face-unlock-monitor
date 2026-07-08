# Nginx / MediaMTX 配置

居家摄像头视频推流服务当前使用 MediaMTX，Nginx 负责将公网视频路径反代到视频流后端。

- RTMP 推流端口：`9090`
- OBS 推流地址：`rtmp://{IP}:9090/stream/{stream_id}`
- 后端 RTSP 地址：`rtsp://127.0.0.1:8554/stream/{stream_id}`
- 视频流后端：`127.0.0.1:8010`
- 主业务后端：`127.0.0.1:8000`
- 典型 stream_id：`1`

生产 Nginx 反代示例：

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

location ^~ /api/ {
    proxy_pass http://127.0.0.1:8000;
}
```
