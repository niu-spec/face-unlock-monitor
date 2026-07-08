## ADDED Requirements

### Requirement: Stream ID mapping

The frontend SHALL maintain a mapping between video stream IDs (`1`, `2`) and business API stream IDs (`living_room`, `kitchen`) in `frontend/src/constants/streams.js`.

#### Scenario: Convert legacy ID to video feed path

- **WHEN** code calls `videoFeedPath('living_room')`
- **THEN** the result is `/video_feed/1`

#### Scenario: Convert video ID for zone API

- **WHEN** code calls `toZoneStreamId('2')`
- **THEN** the result is `kitchen`

### Requirement: Vite dev proxy

The Vite dev server SHALL proxy `/api/` and `/video_feed/` requests to Django at port 8000.

#### Scenario: Local development API call

- **WHEN** the frontend requests `/api/zones/` during `npm run dev`
- **THEN** the request is proxied to `http://localhost:8000/api/zones/`

### Requirement: Trailing slash convention

All Django API paths SHALL use trailing slashes; the Axios client SHALL normalize URLs accordingly.

#### Scenario: Zone list request

- **WHEN** the frontend fetches the zone list
- **THEN** the request URL ends with `/api/zones/` (with trailing slash)

### Requirement: Centralized API module

The frontend SHALL define API functions in `frontend/src/api/index.js` rather than scattering fetch calls across views.

#### Scenario: Zone CRUD via api module

- **WHEN** ZoneEditor creates or updates a zone
- **THEN** it calls functions from `zoneApi` in the centralized API module
