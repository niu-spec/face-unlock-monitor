## MODIFIED Requirements

### Requirement: Alert type taxonomy

The system SHALL support alert types including `FACE_UNKNOWN`, `INTRUSION`, `PROXIMITY`, `LOITER`, `TAILGATE`, `WATER`, `FIRE`, `FALL`, `SCREAM`, `FIGHT`, `CRYING`, `GLASS_BREAK`, `ABNORMAL_SOUND`, and `EMERGENCY`.

#### Scenario: Audio scream alert creation

- **WHEN** the audio detection module detects a scream and calls `create_alert(type="SCREAM", level="HIGH")`
- **THEN** the alert is stored with type `SCREAM` and displayed in AlertCenter with the label "尖叫/呼救声"

#### Scenario: Audio fight alert creation

- **WHEN** the audio detection module detects fighting sounds and calls `create_alert(type="FIGHT", level="HIGH")`
- **THEN** the alert is stored with type `FIGHT` and displayed in AlertCenter with the label "打架/争吵声"

#### Scenario: Audio-video emergency correlation alert

- **WHEN** both a SCREAM audio alert and a FALL video alert occur within a ±5 second time window
- **THEN** an `EMERGENCY` alert SHALL be created with level `CRITICAL` and the description SHALL reference both the audio and video source events

#### Scenario: Glass break alert creation

- **WHEN** the audio detection module detects shattering glass and calls `create_alert(type="GLASS_BREAK", level="MEDIUM")`
- **THEN** the alert is stored with type `GLASS_BREAK`

### Requirement: Alert severity levels

The system SHALL support four alert severity levels: `CRITICAL`, `HIGH`, `MEDIUM`, and `LOW`.

#### Scenario: Emergency alert uses CRITICAL level

- **WHEN** an audio-video correlation EMERGENCY alert is created
- **THEN** the alert level SHALL be `CRITICAL`, indicating the highest priority requiring immediate attention
