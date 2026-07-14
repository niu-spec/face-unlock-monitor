# ai-video-integration Specification

## Purpose

定义 C/D AI 模块接入视频帧处理链（`process_frame()`）的规范，涵盖人脸识别、危险区域闯入与异常检测告警，以及前端 WebRTC + overlay API 展示。

## Requirements

### Requirement: AI video integration pipeline

The system SHALL process each video frame through a chain of AI modules before MJPEG encoding, starting at `process_frame()` in `apps/video_stream/services.py`.

#### Scenario: Face module annotates frame

- **WHEN** the face module is registered in the processing chain
- **THEN** recognized family members receive green bounding boxes and strangers receive red boxes on the output frame

#### Scenario: Detection module triggers intrusion alert

- **WHEN** a child-role person enters a configured kitchen zone polygon
- **THEN** the detection module POSTs an alert with type `INTRUSION` to `/api/alerts/`

#### Scenario: Anomaly detection alerts

- **WHEN** fire or fall conditions are detected in a frame
- **THEN** corresponding alerts with types `FIRE` or `FALL` are created

### Requirement: Presence statistics update

The face module SHALL update person counts accessible via `GET /api/home/presence/` and `GET /api/video/presence/`.

#### Scenario: Poll presence after recognition

- **WHEN** the frontend polls `/api/video/presence/?stream_id={id}`
- **THEN** the response reflects the latest total, family, and stranger counts from the video pipeline

### Requirement: Frontend AI overlay display

The frontend SHALL display AI annotations on the monitor and zone editor pages by overlaying Canvas boxes on WebRTC preview, using overlay data published by the backend video pipeline.

#### Scenario: Monitor page shows AI boxes

- **WHEN** OBS pushes to stream `1` and the user opens the monitor page
- **THEN** person, face, and alert boxes are visible over the WebRTC preview
- **AND** corresponding alerts appear in the alert center

#### Scenario: MJPEG fallback includes burned-in annotations

- **WHEN** a client requests `GET /video_feed/1` during active AI processing
- **THEN** the MJPEG stream includes annotations drawn by the backend before encoding
