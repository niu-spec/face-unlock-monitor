## ADDED Requirements

### Requirement: Stream ID mapping module

The frontend SHALL provide `frontend/src/constants/streams.js` as the single source for converting between video stream IDs (`1`, `2`) and business API IDs (`living_room`, `kitchen`).

#### Scenario: Map legacy ID to video feed

- **WHEN** `videoFeedPath('kitchen')` is called
- **THEN** the result is `/video_feed/2`

#### Scenario: Map video ID for zone API

- **WHEN** `toZoneStreamId('1')` is called
- **THEN** the result is `living_room`
