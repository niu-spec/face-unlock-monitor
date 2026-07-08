# video-stream Specification

## Purpose
TBD - created by archiving change bootstrap-from-docs. Update Purpose after archive.
## Requirements
### Requirement: RTMP ingest via MediaMTX

The system SHALL accept RTMP push streams on port 9090 and expose them as RTSP on port 8554 through MediaMTX.

#### Scenario: OBS push to living room stream

- **WHEN** OBS pushes to `rtmp://{host}:9090/stream/1`
- **THEN** MediaMTX exposes `rtsp://127.0.0.1:8554/stream/1` for backend consumption

### Requirement: MJPEG video feed endpoint

The system SHALL serve live video as MJPEG at `GET /video_feed/{stream_id}` where `stream_id` is the MediaMTX push code (`1` or `2`).

#### Scenario: Browser preview with active stream

- **WHEN** a client requests `GET /video_feed/1` and RTSP source is available
- **THEN** the response is a multipart MJPEG stream showing the camera frame

#### Scenario: No RTSP source available

- **WHEN** a client requests `GET /video_feed/1` and no frames are available
- **THEN** the system SHALL return a placeholder frame or waiting message instead of HTTP 500

### Requirement: Frame processing hook

The video stream service SHALL expose a `process_frame()` extension point so AI modules (face, detection) can annotate frames before MJPEG output.

#### Scenario: AI module registers processor

- **WHEN** an AI module hooks into `process_frame()` in `apps/video_stream/services.py`
- **THEN** each captured frame passes through the processor before encoding to MJPEG

### Requirement: Multi-camera stream mapping

The system SHALL support at least two camera streams: `1` (living room) and `2` (kitchen).

#### Scenario: Kitchen stream access

- **WHEN** OBS pushes to stream code `2`
- **THEN** `GET /video_feed/2` displays the kitchen camera feed

