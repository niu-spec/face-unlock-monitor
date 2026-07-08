# zone-management Specification

## Purpose
TBD - created by archiving change bootstrap-from-docs. Update Purpose after archive.
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

### Requirement: Canvas zone editor

The frontend SHALL provide a Canvas-based editor where users click to add polygon vertices, undo the last point, and clear all points.

#### Scenario: Draw polygon on video background

- **WHEN** a user opens ZoneEditor for stream `kitchen` and clicks 4 points on the canvas overlay
- **THEN** the polygon is rendered on top of the live video background from `/video_feed/2`

#### Scenario: Edit existing zone

- **WHEN** a user clicks a zone row in the table
- **THEN** the polygon vertices load onto the canvas for editing

### Requirement: Role-based zone restriction

Each zone SHALL support `forbidden_roles` (e.g. `["child"]`) to define which family member roles trigger intrusion alerts.

#### Scenario: Kitchen child restriction

- **WHEN** a zone named「厨房」has `forbidden_roles=["child"]`
- **THEN** the detection module SHALL treat child entry into that polygon as an intrusion event

