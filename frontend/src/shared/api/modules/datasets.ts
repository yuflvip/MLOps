import { apiDelete, apiGet, apiPost, apiPut } from '../client'
import type { PaginatedData } from '@/shared/types'

export interface DatasetItem {
  id: number
  name: string
  path: string
  task_type: string | null
  class_names: string[]
  description: string | null
  created_at: string
  updated_at: string
}

export interface DatasetListParams {
  page?: number
  page_size?: number
  name?: string
  path?: string
  task_type?: string
}

export interface DatasetFormPayload {
  name: string
  path: string
  task_type?: string | null
  class_names: string[]
  description?: string | null
}

export function getDatasetList(params?: DatasetListParams) {
  return apiGet<PaginatedData<DatasetItem>, DatasetListParams>('/mlops/datasets', params)
}

export function getDatasetDetail(id: number) {
  return apiGet<DatasetItem>(`/mlops/datasets/${id}`)
}

export function createDataset(data: DatasetFormPayload) {
  return apiPost<DatasetItem, DatasetFormPayload>('/mlops/datasets', data)
}

export function updateDataset(id: number, data: DatasetFormPayload) {
  return apiPut<DatasetItem, DatasetFormPayload>(`/mlops/datasets/${id}`, data)
}

export function deleteDataset(id: number) {
  return apiDelete<boolean>(`/mlops/datasets/${id}`)
}
