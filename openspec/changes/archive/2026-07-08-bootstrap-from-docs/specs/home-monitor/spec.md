## ADDED Requirements

### Requirement: Multi-camera monitor page

The frontend SHALL display a home monitoring page with selectable camera feeds for living room and kitchen.

#### Scenario: Switch camera stream

- **WHEN** a user selects「厨房」on the monitor page
- **THEN** the video element loads `/video_feed/2`

#### Scenario: Video load failure

- **WHEN** the video feed fails to load (no stream available)
- **THEN** the page displays a user-friendly fallback message instead of a broken image

### Requirement: Presence statistics API

The system SHALL expose `GET /api/home/presence/` returning current person counts (total, family, stranger).

#### Scenario: Fetch presence data

- **WHEN** the monitor page polls `/api/home/presence/`
- **THEN** the response includes numeric counts for total, family, and stranger persons

### Requirement: Person stats panel

The monitor page SHALL display a PersonStats component showing total, family, and stranger counts.

#### Scenario: Display stats on load

- **WHEN** the HomeMonitor page mounts
- **THEN** the PersonStats panel shows the latest presence data from the API
