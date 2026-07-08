# Nginx / MediaMTX 配置

居家摄像头视频推流服务当前使用 MediaMTX，Nginx 只负责将 Web/API 请求反代到 Django/Gunicorn。

- RTMP 推流端口：`9090`
- OBS 推流地址：`rtmp://{IP}:9090/stream/{stream_id}`
- 后端 RTSP 地址：`rtsp://127.0.0.1:8554/stream/{stream_id}`
- 典型 stream_id：`1`

生产 Nginx 反代示例：

```nginx
location /video_feed/ {
    proxy_pass http://127.0.0.1:8000/video_feed/;
    proxy_buffering off;
    proxy_cache off;
}

location /api/video/ {
    proxy_pass http://127.0.0.1:8000/api/video/;
}
```
