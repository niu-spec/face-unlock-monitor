## Context

当前 `process_frame()` 仅叠加 stream ID 文字。C 负责人脸识别与人数统计，D 负责 HOG 行人检测、危险区域闯入及积水/着火/跌倒异常检测。

## Goals / Non-Goals

**Goals:**
- 定义帧处理链：face → detection → annotate → return
- 明确告警类型与 API 调用时机
- presence 数据更新路径

**Non-Goals:**
- 不在本 change 中编写完整 AI 算法（由 C/D 实现）
- 不切换 FFmpeg 拉流方案

## Decisions

### 处理器链模式

```python
def process_frame(frame, stream_id):
    frame, events = face_service.process(frame, stream_id)
    frame, alerts = detection_service.process(frame, stream_id)
    emit_events(events + alerts)
    return frame
```

### 告警写入

AI 模块通过 HTTP POST `/api/alerts/` 与 `/api/events/`，不直接写数据库。

## Open Questions

- presence 用轮询还是 WebSocket？当前 spec 保持 GET 轮询。
