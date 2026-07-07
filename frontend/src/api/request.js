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
  return config
})

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (!error.config?.silent) {
      const data = error.response?.data
      const message =
        data?.error ||
        data?.detail ||
        data?.message ||
        error.message ||
        '请求失败'
      ElMessage.error(message)
    }
    return Promise.reject(error)
  },
)

export default request
