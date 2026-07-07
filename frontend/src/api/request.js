import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: '/',
  timeout: 15000,
})

request.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  const householdId = localStorage.getItem('activeHouseholdId')
  if (householdId) {
    config.headers['X-Active-Household-Id'] = householdId
  }
  return config
})

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    // 401 → 清除所有登录状态，跳转登录页
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('refresh')
      localStorage.removeItem('activeHouseholdId')
      localStorage.removeItem('user')
      localStorage.removeItem('households')
      if (window.location.pathname !== '/login' && window.location.pathname !== '/register') {
        window.location.href = '/login'
      }
      return Promise.reject(error)
    }

    if (!error.config?.silent) {
      const data = error.response?.data
      const message = typeof data === 'object'
        ? (data.error || data.detail || data.message || Object.values(data)[0])
        : (data || error.message || '请求失败')
      ElMessage.error(message)
    }
    return Promise.reject(error)
  },
)

export default request
