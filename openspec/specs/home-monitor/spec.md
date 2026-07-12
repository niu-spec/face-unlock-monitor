# home-monitor Specification

## Purpose

居家监控页规格：多路摄像头切换、WebRTC 低延迟预览、后端 AI 叠加层与人数统计。

## Requirements

### Requirement: Multi-camera monitor page

The frontend SHALL display a home monitoring page with selectable camera feeds for living room and kitchen.

#### Scenario: Switch camera stream

- **WHEN** a user selects「厨房」on the monitor page
- **THEN** the page loads WebRTC preview for stream `2` via MediaMTX
- **AND** FaceOverlay renders AI boxes from `/api/video/presence/` or `/api/video/status/`

#### Scenario: Stream unavailable

- **WHEN** no RTSP/WebRTC source is available for the selected stream
- **THEN** the page displays「无推流信号」and clears stale presence data

### Requirement: AI overlay on monitor page

The monitor page SHALL render person, face, and alert bounding boxes on a Canvas overlay aligned to the WebRTC preview, using detection results published by the backend.

#### Scenario: Poll overlay data

- **WHEN** the monitor page polls `/api/video/presence/?stream_id={id}` every 200ms
- **THEN** the response includes `presence.persons`, `presence.face_boxes`, and `presence.alert_boxes` for FaceOverlay rendering

#### Scenario: Liveness status display

- **WHEN** the monitor page receives `liveness` data from the video status API
- **THEN** a status tag shows passed / attack / insufficient states

### Requirement: Presence statistics API

The system SHALL expose `GET /api/home/presence/` and `GET /api/video/presence/` returning current person counts (total, family, stranger).

#### Scenario: Fetch presence data

- **WHEN** the monitor page polls `/api/video/presence/?stream_id=1`
- **THEN** the response includes numeric counts for total, family, and stranger persons

### Requirement: Person stats panel

The monitor page SHALL display a PersonStats component showing total, family, and stranger counts.

#### Scenario: Display stats on load

- **WHEN** the HomeMonitor page mounts
- **THEN** the PersonStats panel shows the latest presence data from the API
