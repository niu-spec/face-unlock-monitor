## Why

当前检测模块仅覆盖**视觉维度**的异常检测（积水、着火、摔倒、禁区闯入），但居家安全场景中存在大量仅靠视觉难以可靠识别的事件：

- **打架/争吵**：视觉易被遮挡，且与打闹难以区分
- **尖叫/呼救**：表情识别需近距离+高分辨率，居家摄像头难以满足
- **玻璃破碎**：碎片太小，YOLO 不可能稳定检测
- **婴儿哭喊**：夜间/昏暗环境视觉完全失效

需要增加**音频维度**的异常事件检测，并通过**音视频联动分析**提高整体检测的可靠性。

## What Changes

- 新增 `audio-detection` capability：从 RTSP 流中提取音频，基于 PANNs CNN14 预训练模型分类异常声音
- 新增 `av-correlation` capability：音视频联动缓冲器，滑动时间窗口内双维度同时触发时升级告警
- 修改 `alerts-events` capability：新增 6 种告警类型和 1 种严重等级
- 集成到 `ai-video-integration` 的视频处理流水线中（并行音频管线）

## Capabilities

### New Capabilities

- `audio-detection`: 异常声学事件检测 — 从 RTSP 抽取音频、PANNs CNN14 分类、异常声音告警
- `av-correlation`: 音视频联动告警 — 滑动时间窗口关联音频与视频事件，升级紧急程度

### Modified Capabilities

- `alerts-events`: 新增 `SCREAM`、`FIGHT`、`CRYING`、`GLASS_BREAK`、`ABNORMAL_SOUND`、`EMERGENCY` 告警类型，新增 `CRITICAL` 严重等级

## Impact

- `backend/apps/detection/audio_capture.py` — 新增：FFmpeg 音频采集子进程管理
- `backend/apps/detection/audio_service.py` — 新增：PANNs CNN14 音频分类与告警
- `backend/apps/detection/av_correlation.py` — 新增：音视频联动缓冲器
- `backend/apps/detection/services.py` — 修改：集成联动缓冲器入队
- `backend/apps/detection/views.py` — 修改：新增 `GET /api/detection/audio/status/`
- `backend/apps/detection/urls.py` — 修改：新增路由
- `backend/apps/alerts/models.py` — 修改：新增告警类型与等级枚举
- `backend/apps/video_stream/services.py` — 修改：CameraWorker 启动时自动开启音频采集
- `backend/requirements.txt` — 修改：新增 `librosa`、`soundfile`、`scipy`、`ffmpeg-python`、`torchaudio`
- `docs/架构设计/AI危险区域与异常检测模块_技术文档.md` — 修改：新增第 9 节技术方案

**状态：代码已实现于 `feature/detection` 分支，OpenSpec 文档本条 change 即为补齐。**
