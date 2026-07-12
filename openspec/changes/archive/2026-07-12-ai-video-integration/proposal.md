## Why

C（人脸识别）和 D（危险区域/异常检测）模块需要接入 `apps/video_stream/services.py` 的 `process_frame()` 钩子，在 MJPEG 输出前完成检测、画框并写入告警/事件 API。前端通过 WebRTC 低延迟预览 + `/api/video/presence/` overlay API 展示 AI 标注。

## What Changes

- 定义 AI 接入 `process_frame()` 的接口契约
- 规范 face/detection 模块与 alerts/events API 的交互
- 拆分 C/D 各自 tasks，供后续 `/opsx-apply` 执行

## Capabilities

### New Capabilities

- `ai-video-integration`: 视频帧 AI 处理流水线与人脸/检测模块接入规范

### Modified Capabilities

- `video-stream`: 扩展 process_frame 为多处理器链式调用

## Impact

- `backend/apps/video_stream/services.py`
- `backend/apps/face/`
- `backend/apps/detection/`
- `GET /api/home/presence/`、`POST /api/alerts/`、`POST /api/events/`

**状态：规格已定义，实现由 C/D 在 feature/face、feature/detection 分支完成。**
