# zone-management Specification

## Purpose

危险区域 CRUD 与前端 Canvas 多边形编辑器规格。

## Requirements

### Requirement: Zone CRUD API

The system SHALL provide REST endpoints at `/api/zones/` for creating, reading, updating, and deleting danger zones.

#### Scenario: Create zone with polygon

- **WHEN** an authenticated client POSTs a zone with `name`, `stream_id`, `points_json`, and `forbidden_roles`
- **THEN** the zone is persisted and returned with an assigned `id`

#### Scenario: List zones by stream

- **WHEN** a client GETs `/api/zones/?stream_id=living_room`
- **THEN** only zones belonging to that stream are returned

### Requirement: Polygon coordinate system

Zone polygons SHALL be stored as JSON arrays of `{x, y}` points in a 640×480 coordinate system.

#### Scenario: Save kitchen polygon

- **WHEN** a user draws a 4-vertex polygon on the 640×480 canvas for the kitchen stream
- **THEN** `points_json` contains exactly those vertex coordinates

### Requirement: Role-based zone restriction

Each zone SHALL support `forbidden_roles` (e.g. `["child"]`) to define which family member roles trigger intrusion alerts.

#### Scenario: Kitchen child restriction

- **WHEN** a zone named「厨房」has `forbidden_roles=["child"]`
- **THEN** the detection module SHALL treat child entry into that polygon as an intrusion event

### Requirement: Canvas polygon editor with video overlay

The ZoneEditor page SHALL render a 640×480 drawing canvas over a WebRTC live preview with optional detection overlay from `/api/video/presence/`, and allow click-to-add polygon vertices.

#### Scenario: Draw new zone on kitchen stream

- **WHEN** user selects kitchen camera and clicks 4 points on the canvas
- **THEN** a closed polygon is displayed over the WebRTC preview and can be saved via zoneApi

#### Scenario: Edit zone from table row

- **WHEN** user clicks an existing zone row
- **THEN** polygon vertices load onto the canvas for modification

### Requirement: Stream-filtered zone list

The ZoneEditor SHALL filter displayed zones by the currently selected camera stream.

#### Scenario: Switch camera filter

- **WHEN** user switches from living room to kitchen stream
- **THEN** only zones with matching `stream_id` are shown in the table
