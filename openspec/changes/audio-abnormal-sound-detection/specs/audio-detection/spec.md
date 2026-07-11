## ADDED Requirements

### Requirement: Real-time audio capture from RTSP

The system SHALL extract the audio track from RTSP streams via a FFmpeg subprocess, outputting PCM s16le mono at 32 kHz in fixed-duration chunks for downstream classification.

#### Scenario: Audio track present

- **WHEN** an RTSP stream contains an audio track
- **THEN** FFmpeg spawns successfully and delivers PCM audio chunks to the callback at the configured interval (default 3 seconds)

#### Scenario: Audio track absent

- **WHEN** an RTSP stream does NOT contain an audio track
- **THEN** the AudioCapture instance enters `degraded` mode and video detection continues unaffected

#### Scenario: FFmpeg not installed

- **WHEN** the `ffmpeg` binary is not found on the system PATH
- **THEN** the AudioCapture instance enters `degraded` mode immediately without crashing the Django process

#### Scenario: FFmpeg subprocess crashes mid-stream

- **WHEN** the FFmpeg subprocess exits unexpectedly during streaming
- **THEN** the system SHALL attempt automatic reconnection up to 3 times before entering `degraded` mode

### Requirement: Abnormal acoustic event classification

The system SHALL classify each audio chunk using a PANNs CNN14 model pretrained on AudioSet, mapping relevant AudioSet classes to business alert types SCREAM, FIGHT, CRYING, and GLASS_BREAK.

#### Scenario: Screaming detected

- **WHEN** the PANNs model outputs > 0.25 confidence for "Screaming", "Shout", or "Yell" classes
- **THEN** a SCREAM alert is created after 2 consecutive confirmations, with level HIGH

#### Scenario: Fighting sounds detected via multi-label logic

- **WHEN** shout/yell class confidence is > 0.20 AND context class (speech noise, hubbub) confidence is elevated
- **THEN** the combined score (shout × 0.7 + context × 0.3) SHALL be computed, and a FIGHT alert SHALL be created after 3 consecutive confirmations if score > 0.25

#### Scenario: Glass breaking detected

- **WHEN** the PANNs model outputs > 0.25 confidence for "Shatter" or "Glass" classes
- **THEN** a GLASS_BREAK alert SHALL be created immediately (single-frame triggering, as glass breaking is an instantaneous event)

#### Scenario: Crying detected

- **WHEN** the PANNs model outputs > 0.25 confidence for "Crying, sobbing" or "Baby cry, infant cry" classes
- **THEN** a CRYING alert SHALL be created after 2 consecutive confirmations, with level MEDIUM

#### Scenario: PANNs model unavailable

- **WHEN** the PANNs CNN14 model fails to load from torch.hub or the fallback checkpoint download
- **THEN** the AudioDetectionService SHALL mark `_model_ready = False` and audio detection SHALL be skipped without affecting video detection

### Requirement: Audio alert cooldown

The system SHALL apply per-type cooldown intervals for audio alerts to prevent duplicate alerts for the same persistent sound event.

#### Scenario: Scream alert cooldown

- **WHEN** a SCREAM alert has been created
- **THEN** subsequent SCREAM detections within 15 seconds SHALL be suppressed

#### Scenario: Fight alert cooldown

- **WHEN** a FIGHT alert has been created
- **THEN** subsequent FIGHT detections within 20 seconds SHALL be suppressed

### Requirement: Audio snippet preservation

The system SHALL save the raw PCM audio chunk that triggered an alert as a WAV file for incident review.

#### Scenario: Audio snippet saved on alert

- **WHEN** a SCREAM, FIGHT, CRYING, or GLASS_BREAK alert is created
- **THEN** a 16-bit 32 kHz mono WAV file SHALL be saved to `snapshots/audio/<stream_id>_<alert_type>_<timestamp>.wav`

### Requirement: Audio detection status endpoint

The system SHALL provide `GET /api/detection/audio/status/` for querying audio detection service health.

#### Scenario: Query audio status with stream filter

- **WHEN** a client GETs `/api/detection/audio/status/?stream_id=kitchen`
- **THEN** the response includes model readiness, capture health, and correlation event buffers for the specified stream

#### Scenario: Query global audio status

- **WHEN** a client GETs `/api/detection/audio/status/`
- **THEN** the response summarizes all active audio capture streams and their degraded/healthy states
