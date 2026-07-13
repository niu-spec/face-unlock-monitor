import request from './request'

// ── 认证 ──────────────────────────────────────────────
export const authApi = {
  login: (data) => request.post('/api/auth/login/', data),
  logout: (refresh) => request.post('/api/auth/logout/', { refresh }),
  register: (data) => request.post('/api/auth/register/', data),
  sendSms: (data) => request.post('/api/auth/sms/send/', data),
  getCaptcha: () => request.get('/api/auth/captcha/'),
  getMe: () => request.get('/api/auth/me/'),
  changePhone: (data) => request.post('/api/auth/change-phone/', data),
  getProfile: () => request.get('/api/auth/profile/'),
  updateProfile: (data) => request.put('/api/auth/profile/update/', data),
}

// ── 家庭管理 ──────────────────────────────────────────
export const householdApi = {
  list: () => request.get('/api/households/'),
  create: (data) => request.post('/api/households/', data),
  remove: (id) => request.delete(`/api/households/${id}/`),
  getMembers: (id) => request.get(`/api/households/${id}/members/`),
  kickMember: (id, userId) => request.post(`/api/households/${id}/kick/`, { user_id: userId }),
  transferAdmin: (id, userId) => request.put(`/api/households/${id}/transfer_admin/`, { user_id: userId }),
  applyJoin: (data) => request.post('/api/households/join/', data),
  getApplications: (id) => request.get(`/api/households/${id}/applications/`),
  reviewApplication: (id, appId, action) => request.put(`/api/households/${id}/review/`, { application_id: appId, action }),
}

// ── 家庭成员 ──────────────────────────────────────────
export const memberApi = {
  list: () => request.get('/api/auth/members/'),
  create: (data) => request.post('/api/auth/members/', data),
  update: (id, data) => request.put(`/api/auth/members/${id}/`, data),
  remove: (id) => request.delete(`/api/auth/members/${id}/`),
}

// ── 人脸注册与识别 ────────────────────────────────────
export const faceApi = {
  register: (data) => request.post('/api/face/register/', data),
  analyze: (data) => request.post('/api/face/analyze/', data),
  liveness: (data) => request.post('/api/face/liveness/', data),
}

// ── 区域 ──────────────────────────────────────────────
export const zoneApi = {
  list: () => request.get('/api/zones/'),
  create: (data) => request.post('/api/zones/', data),
  update: (id, data) => request.put(`/api/zones/${id}/`, data),
  remove: (id) => request.delete(`/api/zones/${id}/`),
}

// ── 告警 ──────────────────────────────────────────────
export const alertApi = {
  list: (params) => request.get('/api/alerts/', { params }),
  handle: (id) => request.put(`/api/alerts/${id}/handle/`),
  ignore: (id) => request.put(`/api/alerts/${id}/ignore/`),
  batchHandle: (ids) => request.put('/api/alerts/batch-handle/', { ids }),
  batchIgnore: (ids) => request.put('/api/alerts/batch-ignore/', { ids }),
}

// ── 事件 ──────────────────────────────────────────────
export const eventApi = {
  list: (params) => request.get('/api/events/', { params }),
}

export function fetchSnapshotBlob(filename) {
  if (!filename) return Promise.resolve(null)
  return request.get(`/api/snapshots/${encodeURIComponent(filename)}/`, {
    responseType: 'blob',
    silent: true,
  })
}

export function fetchClipBlob(filename) {
  if (!filename) return Promise.resolve(null)
  return request.get(`/api/clips/${encodeURIComponent(filename)}/`, {
    responseType: 'blob',
    silent: true,
  })
}

// ── 监控日报 ──────────────────────────────────────────
export const reportApi = {
  list: () => request.get('/api/reports/daily/'),
  detail: (id) => request.get(`/api/reports/daily/${id}/`),
  generate: (data = {}) => request.post('/api/reports/daily/generate/', data),
}

// ── 摄像头 ────────────────────────────────────────────
export const cameraApi = {
  list: () => request.get('/api/cameras/'),
  create: (data) => request.post('/api/cameras/', data),
  remove: (id) => request.delete(`/api/cameras/${id}/`),
}

// ── 人数统计 ──────────────────────────────────────────
export const homeApi = {
  presence: (streamId) =>
    request.get('/api/home/presence/', {
      params: streamId ? { stream_id: streamId } : {},
      silent: true,
    }),
}

// ── 视频流状态（与 MJPEG 同进程，含实时 presence）──────
export const videoApi = {
  status: (streamId) =>
    request.get('/api/video/status', {
      params: streamId ? { stream_id: streamId } : {},
      silent: true,
    }),
  presence: (streamId) =>
    request.get('/api/video/presence', {
      params: streamId ? { stream_id: streamId } : {},
      silent: true,
    }),
}

// ── 通知配置 ──────────────────────────────────────────
export const notificationApi = {
  getConfig: () => request.get('/api/notifications/config/'),
  updateConfig: (data) => request.put('/api/notifications/config/', data),
  testWebhook: () => request.post('/api/notifications/config/test/'),
}

export { videoFeedPath as videoFeedUrl, webrtcPreviewUrl } from '@/constants/streams'
