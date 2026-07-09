/**
 * 摄像头流 ID 约定
 *
 * - id: MediaMTX / video_stream 使用的推流码（OBS 推 stream/1 → /video_feed/1）
 * - legacyId: Django 业务层 zones/alerts/events 沿用的 stream_id
 */
export const CAMERA_STREAMS = [
  { id: '1', label: '客厅', legacyId: 'living_room' },
  { id: '2', label: '厨房', legacyId: 'kitchen' },
]

export const DEFAULT_STREAM_ID = '1'

export function getStreamById(id) {
  return CAMERA_STREAMS.find((s) => s.id === id)
}

export function getStreamByLegacyId(legacyId) {
  return CAMERA_STREAMS.find((s) => s.legacyId === legacyId)
}

/** 视频预览 /video_feed/{id} */
export function toVideoStreamId(streamId) {
  return getStreamByLegacyId(streamId)?.id ?? streamId
}

/** 区域/告警等业务 API 的 stream_id */
export function toZoneStreamId(videoStreamId) {
  return getStreamById(videoStreamId)?.legacyId ?? videoStreamId
}

export function videoFeedPath(streamId) {
  return `/video_feed/${toVideoStreamId(streamId)}?ts=${Date.now()}`
}

/** WebRTC 低延迟预览（MediaMTX :8889） */
export function webrtcPreviewUrl(streamId) {
  const base = (import.meta.env.VITE_WEBRTC_BASE_URL || 'http://152.136.29.158:8889').replace(/\/$/, '')
  return `${base}/stream/${toVideoStreamId(streamId)}/`
}
