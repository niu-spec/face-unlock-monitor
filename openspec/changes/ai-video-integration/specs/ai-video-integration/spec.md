## ADDED Requirements

### Requirement: AI video integration pipeline

The system SHALL process each video frame through a chain of AI modules before MJPEG encoding, starting at `process_frame()` in `apps/video_stream/services.py`.

#### Scenario: Face module annotates frame

- **WHEN** the face module is registered in the processing chain
- **THEN** recognized family members receive green bounding boxes and strangers receive red boxes on the output frame

#### Scenario: Detection module triggers intrusion alert

- **WHEN** a child-role person enters a configured kitchen zone polygon
- **THEN** the detection module POSTs an alert with type `INTRUSION` to `/api/alerts/`

#### Scenario: Anomaly detection alerts

- **WHEN** water, fire, or fall conditions are detected in a frame
- **THEN** corresponding alerts with types `WATER`, `FIRE`, or `FALL` are created

### Requirement: Presence statistics update

The face module SHALL update person counts accessible via `GET /api/home/presence/`.

#### Scenario: Poll presence after recognition

- **WHEN** the frontend polls `/api/home/presence/`
- **THEN** the response reflects the latest total, family, and stranger counts from the video pipeline
