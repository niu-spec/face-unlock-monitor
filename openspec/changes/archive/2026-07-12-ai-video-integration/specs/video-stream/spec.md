## MODIFIED Requirements

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
