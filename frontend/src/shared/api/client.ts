import axios, { type AxiosInstance } from 'axios'
import { ElMessage } from 'element-plus'
import type { ApiEnvelope } from '@/shared/types'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

const http: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// Response interceptor — unwrap envelope
http.interceptors.response.use(
  (response) => {
    if (response.config.responseType === 'blob') return response
    const body = response.data as ApiEnvelope<unknown>
    if (body.code !== 0) {
      const msg = body.message || '请求失败'
      ElMessage.error(msg)
      return Promise.reject(new Error(msg))
    }
    return response
  },
  (error) => {
    if (error.response) {
      const body = error.response.data as { message?: string } | undefined
      const msg = body?.message || `请求错误 (${error.response.status})`
      ElMessage.error(msg)
    } else if (error.code === 'ECONNABORTED') {
      ElMessage.error('请求超时，请稍后重试')
    } else {
      ElMessage.error('网络连接失败')
    }
    return Promise.reject(error)
  },
)

/** Typed GET — returns data field from envelope */
export async function apiGet<T, P = Record<string, unknown>>(url: string, params?: P): Promise<T> {
  const res = await http.get<ApiEnvelope<T>>(url, { params })
  return res.data.data
}

/** Typed POST — returns data field from envelope */
export async function apiPost<T, D = Record<string, unknown>>(url: string, data?: D): Promise<T> {
  const res = await http.post<ApiEnvelope<T>>(url, data)
  return res.data.data
}

/** Typed PUT — returns data field from envelope */
export async function apiPut<T, D = Record<string, unknown>>(url: string, data?: D): Promise<T> {
  const res = await http.put<ApiEnvelope<T>>(url, data)
  return res.data.data
}

/** Typed DELETE — returns data field from envelope */
export async function apiDelete<T>(url: string): Promise<T> {
  const res = await http.delete<ApiEnvelope<T>>(url)
  return res.data.data
}

/** POST that returns full envelope (for warnings access) */
export async function apiPostFull<T, D = Record<string, unknown>>(url: string, data?: D): Promise<ApiEnvelope<T>> {
  const res = await http.post<ApiEnvelope<T>>(url, data)
  return res.data
}

export { http }
