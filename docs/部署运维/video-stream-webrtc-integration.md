# 视频推流与低延迟 WebRTC 预览对接说明

本文档面向前端组、AI 人脸识别组、数据库/后端组、测试组，说明当前项目的视频推流、低延迟预览、MJPEG 备用预览和识别接入方式。当前项目已经从原来的 MJPEG 预览架构，升级为 WebRTC 低延迟预览 + MJPEG 备用预览的双通道架构。

## 1. 当前整体架构

当前视频链路分为四个协作部分：推流输入链路、低延迟 WebRTC 预览链路、MJPEG 备用预览链路、AI 人脸识别链路。

### 1.1 推流输入链路

```text
摄像头 / OBS / 手机推流 App
  -> RTMP
  -> MediaMTX
```

推流地址规则：

```text
rtmp://152.136.29.158:9090/stream/<stream_id>
```

示例：

```text
stream/1: rtmp://152.136.29.158:9090/stream/1
stream/2: rtmp://152.136.29.158:9090/stream/2
```

### 1.2 低延迟 WebRTC 预览链路

```text
摄像头 / OBS / 手机
  -> RTMP 9090
  -> MediaMTX
  -> WebRTC 8889/8189
  -> 浏览器
```

观看地址：

```text
http://152.136.29.158:8889/stream/<stream_id>/
```

示例：

```text
摄像头 1: http://152.136.29.158:8889/stream/1/
摄像头 2: http://152.136.29.158:8889/stream/2/
```

这是当前推荐前端默认使用的低延迟预览方式，延迟已经测试可降到 1 秒以内。

### 1.3 MJPEG 备用预览链路

```text
摄像头 / OBS / 手机
  -> RTMP 9090
  -> MediaMTX
  -> RTSP 8554
  -> Django/OpenCV 8010
  -> MJPEG /video_feed/<stream_id>
  -> 浏览器
```

备用观看地址：

```text
http://152.136.29.158/video_feed/1
http://152.136.29.158/video_feed/2
```

MJPEG 链路延迟较高，但保留作为兼容备用和调试入口。

### 1.4 AI 人脸识别链路

AI 组不要从 WebRTC 页面截图，也不要优先从 `/video_feed` 抽图。推荐后端从 RTSP 或 CameraWorker 获取帧：

```text
rtsp://127.0.0.1:8554/stream/1
rtsp://127.0.0.1:8554/stream/2
```

识别结果写入数据库，前端通过 API 或后续 WebSocket 展示识别结果。

## 2. 当前服务与端口配置

| 服务 | 作用 | 地址 / 端口 |
|---|---|---|
| MediaMTX RTMP | 接收 OBS/手机推流 | 152.136.29.158:9090 |
| MediaMTX RTSP | 供 Django/OpenCV 内部拉流 | 127.0.0.1:8554 |
| MediaMTX WebRTC HTTP | 浏览器低延迟预览页面 | 152.136.29.158:8889 |
| MediaMTX WebRTC ICE | WebRTC UDP 连接 | 8189/udp |
| Django 视频后端 | 视频 API、MJPEG 备用流 | 127.0.0.1:8010 |
| mini-rednote 主业务后端 | 主业务 API / admin | 127.0.0.1:8000 |
| MySQL 8 | 业务数据库 | 127.0.0.1:3307 |
| Nginx | 公网入口、反向代理 | 80 / 443 |

说明：

- 9090、8554、8889、8189 由 MediaMTX 提供。
- 8010 是 home-camera-monitor 视频后端。
- 8000 是 mini-rednote 主业务后端。
- 不要把视频后端重新绑定到 8000。
- 8889 是 TCP。
- 8189 是 UDP。
- 腾讯云安全组和宝塔安全都需要放行 8889 TCP 和 8189 UDP。

## 3. 当前 Docker / systemd 配置

正式 MediaMTX 当前应以类似方式启动：

```bash
docker run -d --name home-mediamtx --restart=always \
  -p 9090:1935 \
  -p 8554:8554 \
  -p 8889:8889 \
  -p 8189:8189/udp \
  -e MTX_WEBRTCADDITIONALHOSTS=152.136.29.158 \
  -e MTX_WEBRTCLOCALUDPADDRESS=:8189 \
  bluenviron/mediamtx:latest
```

注意：上面的命令用于说明当前部署形态，不要随意执行重建。重建 MediaMTX 会短暂中断所有视频推流。

视频后端 systemd 服务：

```text
home-camera-backend.service
```

绑定地址：

```text
127.0.0.1:8010
```

Gunicorn 推荐配置：

| 配置项 | 推荐值 |
|---|---|
| workers | 1 |
| threads | 16 |
| timeout | 300 |

## 4. 摄像头推流规则

每一路摄像头使用一个独立 `stream_id`，推流码就是 `stream_id`。

| 摄像头 | RTMP 服务器 | 推流码 | 完整推流地址 | WebRTC 低延迟预览 | MJPEG 备用预览 |
|---|---|---|---|---|---|
| 摄像头 1 | rtmp://152.136.29.158:9090/stream | 1 | rtmp://152.136.29.158:9090/stream/1 | http://152.136.29.158:8889/stream/1/ | http://152.136.29.158/video_feed/1 |
| 摄像头 2 | rtmp://152.136.29.158:9090/stream | 2 | rtmp://152.136.29.158:9090/stream/2 | http://152.136.29.158:8889/stream/2/ | http://152.136.29.158/video_feed/2 |
| 摄像头 3 | rtmp://152.136.29.158:9090/stream | 3 | rtmp://152.136.29.158:9090/stream/3 | http://152.136.29.158:8889/stream/3/ | http://152.136.29.158/video_feed/3 |
| 摄像头 4 | rtmp://152.136.29.158:9090/stream | 4 | rtmp://152.136.29.158:9090/stream/4 | http://152.136.29.158:8889/stream/4/ | http://152.136.29.158/video_feed/4 |

强调：

- 不同摄像头不能使用同一个推流码。
- 两台设备同时使用 `stream/1` 会互相冲突。
- 前端访问 WebRTC 地址时，只有对应 `stream_id` 正在推流才会有画面。
- 如果没有推流，MediaMTX 日志可能出现 `no stream is available on path 'stream/x'`，这是正常的离线状态。

## 5. OBS 推流配置

OBS 配置方式：

| 配置项 | 填写内容 |
|---|---|
| 服务 | 自定义 |
| 服务器 | rtmp://152.136.29.158:9090/stream |
| 推流码 | 按摄像头编号填写，例如 1、2、3 |

输出配置建议：

| 配置项 | 推荐值 |
|---|---|
| 编码器 | H.264 / NVENC H.264 / x264 |
| 不要使用 | H.265 / HEVC |
| 速率控制 | CBR |
| 码率 | 500~800 Kbps |
| 关键帧间隔 | 1 秒 |
| B 帧 / 最大 B 帧 | 0 |
| Profile | baseline 或 main |
| 分辨率 | 640x360 |
| FPS | 15 或 20 |
| Look-ahead | 关闭 |
| Psycho Visual Tuning | 关闭 |
| Multipass | Single Pass |
| 音频 | 可关闭，或 AAC |

重点说明：WebRTC 不支持带 B 帧的 H.264。如果出现：

```text
WebRTC doesn't support H264 streams with B-frames
```

说明 OBS 的 B 帧没有关闭，需要将 B 帧设置为 0，并停止直播后重新开始直播。

## 6. 手机推流 App 配置

手机推流 App 可以使用 Larix Broadcaster、PRISM Live Studio、CameraFi Live 等。

如果 App 分开填写：

| 配置项 | 填写内容 |
|---|---|
| 协议 | RTMP |
| 服务器 | rtmp://152.136.29.158:9090/stream |
| 推流码 | 1 或 2 或 3 |

如果 App 只能填写完整地址：

```text
rtmp://152.136.29.158:9090/stream/1
rtmp://152.136.29.158:9090/stream/2
```

手机推流建议：

| 配置项 | 推荐值 |
|---|---|
| 协议 | RTMP |
| 编码 | H.264 / AVC |
| 不要使用 | H.265 / HEVC |
| 分辨率 | 640x360 |
| FPS | 15 |
| 码率 | 500~800 Kbps |
| 关键帧间隔 | 1 秒 |
| 音频 | 关闭或 AAC |
| 网络 | 优先稳定 WiFi / 5G，不建议弱校园网 |

## 7. 前端组对接方式

前端默认使用 WebRTC 低延迟预览，MJPEG 作为备用。

推荐摄像头卡片结构：

- 摄像头名称
- WebRTC 低延迟预览
- MJPEG 备用预览按钮
- `stream_id`
- 推流地址说明
- 在线/离线状态

最简单实现可以用 iframe：

```html
<iframe
  src="http://152.136.29.158:8889/stream/1/"
  style="width: 100%; height: 360px; border: none; background: #000;"
  allow="autoplay; fullscreen">
</iframe>
```

摄像头 2：

```html
<iframe
  src="http://152.136.29.158:8889/stream/2/"
  style="width: 100%; height: 360px; border: none; background: #000;"
  allow="autoplay; fullscreen">
</iframe>
```

备用 MJPEG：

```html
<img src="http://152.136.29.158/video_feed/1" />
```

接入注意事项：

- 默认展示 WebRTC。
- 如果 WebRTC 因网络或浏览器限制不可用，提供“备用 MJPEG 预览”按钮。
- 如果前端页面是 HTTPS，而 WebRTC 页面是 HTTP，浏览器可能阻止 iframe 混合内容。短期可以使用“新窗口打开 WebRTC”按钮，长期再做 HTTPS 反代或 MediaMTX HTTPS 配置。
- 不要在同一个页面重复创建多个相同 `stream_id` 的视频连接。
- 多摄像头页面不要无脑加载 4 路以上，避免浪费带宽。

建议的前端入口：

```text
/camera-dashboard-webrtc
```

这个页面应默认使用 WebRTC 地址：

```text
http://152.136.29.158:8889/stream/1/
http://152.136.29.158:8889/stream/2/
```

同时保留 MJPEG 备用地址：

```text
http://152.136.29.158/video_feed/1
http://152.136.29.158/video_feed/2
```

## 8. AI / 人脸识别组对接方式

WebRTC 只负责低延迟播放，不负责识别。AI 组应从 RTSP / CameraWorker 抽帧做人脸识别：

```text
rtsp://127.0.0.1:8554/stream/1
rtsp://127.0.0.1:8554/stream/2
```

不要从 WebRTC 页面截图识别，也不要优先从 `/video_feed` 抽图识别。

推荐架构：

```text
MediaMTX: 接收推流、提供 WebRTC 和 RTSP
Django/OpenCV: 从 RTSP 抽帧做人脸检测和识别
MySQL: 保存识别记录
前端: 播放 WebRTC 视频，同时展示识别结果
```

识别逻辑要求：

- 不要阻塞 WebRTC 播放。
- 不要阻塞 MJPEG 输出。
- 识别应异步执行。
- 可每 3~5 帧抽一帧识别。
- 同一个人短时间内不要重复写入大量识别记录。
- 识别结果通过 API 或后续 WebSocket 推给前端。

## 9. 后端 / 数据库组对接方式

保留现有视频 API：

```text
GET http://152.136.29.158/api/video/status
GET http://152.136.29.158/api/video/streams/1/source
GET http://152.136.29.158/api/video/streams/2/source
```

这些 API 可用于：

- 获取视频服务状态。
- 获取 `stream_id` 对应的 RTMP / RTSP / MJPEG 地址。
- 给前端展示推流说明。

数据库信息只写以下内容：

```text
MySQL 8
Host: 127.0.0.1
Port: 3307
Database: home_camera_monitor
```

不要把数据库密码写入文档，不要提交任何密钥、密码、token。

## 10. 常见问题与排查

| 问题 | 排查命令 / 处理方式 | 可能原因 |
|---|---|---|
| WebRTC 页面打开但黑屏 | `docker logs --since=60s home-mediamtx \| grep -E "WebRTC\|stream/1\|B-frames\|deadline\|established\|reading\|closed\|error"` | OBS 没有推流、推流码错误、8189 UDP 没放行、OBS B 帧没有设置为 0、使用了 H.265 / HEVC |
| 日志出现 `no stream is available on path 'stream/2'` | 启动第二路推流即可；如果暂时不用第二路，可以忽略 | `stream/2` 当前没有推流 |
| 日志出现 `WebRTC doesn't support H264 streams with B-frames` | 设置 OBS B 帧为 0，并重新开始直播 | OBS B 帧未关闭 |
| 日志出现 `deadline exceeded while waiting connection` | 重点检查腾讯云安全组和宝塔安全是否放行 8189 UDP | WebRTC ICE 连接失败 |
| WebRTC 能看但 `/video_feed` 延迟高 | 使用 WebRTC 作为正式预览，MJPEG 只作为备用 | `/video_feed` 是 MJPEG 备用链路，延迟本身较高 |
| HTTPS 页面中 iframe 加载 HTTP WebRTC 被拦截 | 短期使用“新窗口打开 WebRTC”按钮；长期通过 Nginx 做 HTTPS 反代，或为 MediaMTX 配置 HTTPS | 浏览器混合内容限制 |

## 11. 常用检查命令

检查 MediaMTX 端口：

```bash
docker ps --format 'table {{.Names}}\t{{.Ports}}' | grep home-mediamtx
ss -lntup | grep -E "9090|8554|8889|8189"
```

检查视频后端：

```bash
systemctl status home-camera-backend.service --no-pager -l
curl -i http://127.0.0.1:8010/api/video/status
```

检查 `stream/1` 日志：

```bash
docker logs --since=2m home-mediamtx | grep -E "stream/1|publishing|WebRTC|B-frames|deadline|established|reading|closed|error"
```

检查 `stream/2` 日志：

```bash
docker logs --since=2m home-mediamtx | grep -E "stream/2|publishing|WebRTC|B-frames|deadline|established|reading|closed|error"
```

重启视频后端：

```bash
systemctl restart home-camera-backend.service
```

注意：不要随便重启 `home-mediamtx`。重启 MediaMTX 会断开所有正在推流的摄像头。

## 12. 当前最终结论

当前项目已经完成 WebRTC 低延迟预览架构改造。

推荐使用：

```text
WebRTC:
http://152.136.29.158:8889/stream/1/
http://152.136.29.158:8889/stream/2/
```

作为主视频预览方式。

保留：

```text
http://152.136.29.158/video_feed/1
http://152.136.29.158/video_feed/2
```

作为兼容备用方式。

Django 后端不再承担主视频播放链路，主要负责视频 API、RTSP 抽帧、人脸识别、数据库记录和业务接口。
