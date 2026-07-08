## ADDED Requirements

### Requirement: Canvas polygon editor with video overlay

The ZoneEditor page SHALL render a 640×480 canvas over a live video background from `/video_feed/{id}` and allow click-to-add polygon vertices.

#### Scenario: Draw new zone on kitchen stream

- **WHEN** user selects kitchen camera and clicks 4 points on the canvas
- **THEN** a closed polygon is displayed and can be saved via zoneApi

#### Scenario: Edit zone from table row

- **WHEN** user clicks an existing zone row
- **THEN** polygon vertices load onto the canvas for modification

### Requirement: Stream-filtered zone list

The ZoneEditor SHALL filter displayed zones by the currently selected camera stream.

#### Scenario: Switch camera filter

- **WHEN** user switches from living room to kitchen stream
- **THEN** only zones with matching `stream_id` are shown in the table
