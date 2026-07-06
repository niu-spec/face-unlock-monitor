import request from './request'

export const authApi = {
  login: (data) => request.post('/api/auth/login', data),
}

export const homeApi = {
  presence: () => request.get('/api/home/presence'),
}

export const faceApi = {
  register: (data) => request.post('/api/face/register', data),
}

export const zoneApi = {
  list: () => request.get('/api/zones'),
  create: (data) => request.post('/api/zones', data),
  update: (id, data) => request.put(`/api/zones/${id}`, data),
  remove: (id) => request.delete(`/api/zones/${id}`),
}

export const alertApi = {
  list: (params) => request.get('/api/alerts', { params }),
  handle: (id, data) => request.put(`/api/alerts/${id}/handle`, data),
}

export const eventApi = {
  list: (params) => request.get('/api/events', { params }),
}

export const logApi = {
  list: (params) => request.get('/api/logs', { params }),
  replay: (id) => request.get(`/api/replay/${id}`),
}

export const videoFeedUrl = (streamId) => `/video_feed/${streamId}`
