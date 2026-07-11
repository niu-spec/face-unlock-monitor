# alerts-events Specification

## Purpose
TBD - created by archiving change bootstrap-from-docs. Update Purpose after archive.
## Requirements
### Requirement: Alert listing and creation

The system SHALL provide `GET /api/alerts/` for listing alerts and `POST /api/alerts/` for creating alerts (used by AI modules).

#### Scenario: List recent alerts

- **WHEN** a client GETs `/api/alerts/`
- **THEN** alerts are returned ordered by creation time with fields including `type`, `stream_id`, and `status`

#### Scenario: AI creates intrusion alert

- **WHEN** the detection module POSTs an alert with `type=INTRUSION` and `stream_id=kitchen`
- **THEN** the alert is persisted and visible in the alert list

### Requirement: Alert handling

The system SHALL allow marking alerts as handled via `PUT /api/alerts/{id}/handle/`.

#### Scenario: User handles alert

- **WHEN** an authenticated user submits a handle action for alert id 5
- **THEN** the alert status updates to handled

### Requirement: Event log

The system SHALL provide `GET /api/events/` and `POST /api/events/` for event logging and retrieval.

#### Scenario: Log detection event

- **WHEN** an AI module POSTs an event with `event_type`, `stream_id`, and `description`
- **THEN** the event appears in the event log list

### Requirement: Alert type taxonomy

The system SHALL support alert types including `FACE_UNKNOWN`, `INTRUSION`, `PROXIMITY`, `LOITER`, `TAILGATE`, `WATER`, `FIRE`, `FALL`, `SCREAM`, `FIGHT`, `CRYING`, `GLASS_BREAK`, `ABNORMAL_SOUND`, and `EMERGENCY`.

#### Scenario: Fire alert creation

- **WHEN** the detection module detects fire and POSTs `type=FIRE`
- **THEN** the alert is stored with type `FIRE` and displayed in AlertCenter

#### Scenario: Audio scream alert creation

- **WHEN** the audio detection module detects a scream and POSTs `type=SCREAM`
- **THEN** the alert is stored with type `SCREAM` and displayed in AlertCenter

#### Scenario: Audio-video emergency correlation

- **WHEN** both audio and video anomalies co-occur within ±5s
- **THEN** an `EMERGENCY` alert SHALL be created with level `CRITICAL`

### Requirement: Alert severity levels

The system SHALL support severity levels `CRITICAL`, `HIGH`, `MEDIUM`, and `LOW`.

#### Scenario: Emergency uses CRITICAL

- **WHEN** an audio-video emergency is detected
- **THEN** the alert level SHALL be `CRITICAL`

### Requirement: Frontend alert center

The frontend SHALL provide an AlertCenter view for browsing and handling alerts.

#### Scenario: View alert list

- **WHEN** a user navigates to AlertCenter
- **THEN** alerts are fetched from `/api/alerts/` and displayed in a table

