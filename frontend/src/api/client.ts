import axios from 'axios'
import { ElMessage } from 'element-plus'
import { clearStoredToken, getStoredToken } from './authToken'

const client = axios.create({
  baseURL: '/',
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' },
})

client.interceptors.request.use((config) => {
  const token = getStoredToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

client.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status
    const msg = error.response?.data?.detail || error.message || '请求失败'
    if (status === 401 && window.location.pathname !== '/login') {
      clearStoredToken()
      window.location.href = '/login'
    } else {
      ElMessage.error(msg)
    }
    return Promise.reject(error)
  }
)

export default client
