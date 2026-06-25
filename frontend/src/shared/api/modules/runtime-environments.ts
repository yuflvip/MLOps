import { apiDelete, apiGet, apiPost, apiPut } from '../client'
import type { PaginatedData } from '@/shared/types'

export interface RuntimeEnvironmentItem {
  id: number
  code: string
  name: string
  description: string | null
  env_type: 'python' | 'conda' | 'docker'
  python_path: string | null
  working_dir: string | null
  docker_image: string | null
  extra_env: Record<string, string>
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface RuntimeEnvironmentListParams {
  page?: number
  page_size?: number
  code?: string
  name?: string
  env_type?: string
  is_active?: boolean
}

export interface RuntimeEnvironmentFormPayload {
  code: string
  name: string
  description?: string | null
  env_type: 'python' | 'conda' | 'docker'
  python_path?: string | null
  working_dir?: string | null
  docker_image?: string | null
  extra_env?: Record<string, string>
  is_active: boolean
}

export function getRuntimeEnvironmentList(params?: RuntimeEnvironmentListParams) {
  return apiGet<PaginatedData<RuntimeEnvironmentItem>, RuntimeEnvironmentListParams>(
    '/mlops/runtime-environments',
    params,
  )
}

export function getRuntimeEnvironmentDetail(id: number) {
  return apiGet<RuntimeEnvironmentItem>(`/mlops/runtime-environments/${id}`)
}

export function createRuntimeEnvironment(data: RuntimeEnvironmentFormPayload) {
  return apiPost<RuntimeEnvironmentItem, RuntimeEnvironmentFormPayload>(
    '/mlops/runtime-environments',
    data,
  )
}

export function updateRuntimeEnvironment(id: number, data: RuntimeEnvironmentFormPayload) {
  return apiPut<RuntimeEnvironmentItem, RuntimeEnvironmentFormPayload>(
    `/mlops/runtime-environments/${id}`,
    data,
  )
}

export function deleteRuntimeEnvironment(id: number) {
  return apiDelete<boolean>(`/mlops/runtime-environments/${id}`)
}
