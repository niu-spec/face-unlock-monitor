# video-stream Specification

## Purpose

视频推拉流与后端 AI 处理链规格：MediaMTX 接入、MJPEG 备用输出、overlay 快照 API。

## Requirements

### Requirement: RTMP ingest via MediaMTX

The system SHALL accept RTMP push streams on port 9090 and expose them as RTSP on port 8554 through MediaMTX.

#### Scenario: OBS push to living room stream

- **WHEN** OBS pushes to `rtmp://{host}:9090/stream/1`
- **THEN** MediaMTX exposes `rtsp://127.0.0.1:8554/stream/1` for backend consumption

### Requirement: MJPEG video feed endpoint

The system SHALL serve live video as MJPEG at `GET /video_feed/{stream_id}` where `stream_id` is the MediaMTX push code (`1` or `2`). MJPEG is a backend output path for debugging and fallback; the frontend monitor page uses WebRTC for primary preview.

#### Scenario: Browser preview with active stream

- **WHEN** a client requests `GET /video_feed/1` and RTSP source is available
- **THEN** the response is a multipart MJPEG stream showing the camera frame

#### Scenario: MJPEG includes backend AI annotations

- **WHEN** a client requests `GET /video_feed/1` while AI modules are active
- **THEN** each MJPEG frame includes bounding boxes drawn by `process_frame()` before encoding

#### Scenario: No RTSP source available

- **WHEN** a client requests `GET /video_feed/1` and no frames are available
- **THEN** the system SHALL return a placeholder frame or waiting message instead of HTTP 500

### Requirement: Frame processing hook

The video stream service SHALL expose a `process_frame()` extension point that supports a chain of AI processors (face, detection) before MJPEG output.

#### Scenario: Chained AI processors

- **WHEN** multiple AI modules register with `process_frame()`
- **THEN** each frame passes through all processors in order before encoding

#### Scenario: AI module registers processor

- **WHEN** an AI module hooks into `process_frame()` in `apps/video_stream/services.py`
- **THEN** each captured frame passes through the processor before encoding to MJPEG

### Requirement: Overlay snapshot API

The system SHALL expose per-stream detection overlay data via `GET /api/video/presence/` and `GET /api/video/status/` for frontend Canvas rendering over WebRTC preview.

#### Scenario: Presence includes overlay boxes

- **WHEN** a client GETs `/api/video/presence/?stream_id=1` during active streaming
- **THEN** the response includes `presence.persons`, `presence.face_boxes`, `presence.alert_boxes`, and `presence.frame_size`

### Requirement: Multi-camera stream mapping

The system SHALL support at least two camera streams: `1` (living room) and `2` (kitchen).

#### Scenario: Kitchen stream access

- **WHEN** OBS pushes to stream code `2`
- **THEN** `GET /video_feed/2` displays the kitchen camera feed with AI annotations
