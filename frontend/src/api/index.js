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
}

// ── 事件 ──────────────────────────────────────────────
export const eventApi = {
  list: (params) => request.get('/api/events/', { params }),
}

// ── 摄像头 ────────────────────────────────────────────
export const cameraApi = {
  list: () => request.get('/api/cameras/'),
  create: (data) => request.post('/api/cameras/', data),
  remove: (id) => request.delete(`/api/cameras/${id}/`),
}

// ── 人数统计 ──────────────────────────────────────────
export const homeApi = {
  presence: () => request.get('/api/home/presence/', { silent: true }),
}

export { videoFeedPath as videoFeedUrl, webrtcPreviewUrl } from '@/constants/streams'
