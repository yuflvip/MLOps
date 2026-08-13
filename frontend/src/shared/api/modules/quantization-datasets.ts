import { apiDelete, apiGet, apiPost, apiPut, http } from '../client'
import type { PaginatedData } from '@/shared/types'

export interface QuantizationDatasetItem {
  id: number
  name: string
  storage_path: string
  image_list_path: string
  image_count: number
  size_bytes: number
  description: string | null
  created_at: string | null
  updated_at: string | null
}

export interface QuantizationImageItem {
  name: string
  size_bytes: number
  modified_at: string
}

export interface QuantizationDatasetCreateForm {
  name: string
  directory_name: string
  description?: string | null
}

export interface QuantizationDatasetUpdateForm {
  name: string
  description?: string | null
}

export interface QuantizationImageUploadResult {
  image: QuantizationImageItem
  dataset: QuantizationDatasetItem
}

export function getQuantizationDatasetList(params: {
  page: number
  page_size: number
  name?: string
}) {
  return apiGet<PaginatedData<QuantizationDatasetItem>, typeof params>(
    '/mlops/quantization-datasets',
    params,
  )
}

export function getQuantizationDataset(id: number) {
  return apiGet<QuantizationDatasetItem>(`/mlops/quantization-datasets/${id}`)
}

export function createQuantizationDataset(data: QuantizationDatasetCreateForm) {
  return apiPost<QuantizationDatasetItem, QuantizationDatasetCreateForm>(
    '/mlops/quantization-datasets',
    data,
  )
}

export function updateQuantizationDataset(id: number, data: QuantizationDatasetUpdateForm) {
  return apiPut<QuantizationDatasetItem, QuantizationDatasetUpdateForm>(
    `/mlops/quantization-datasets/${id}`,
    data,
  )
}

export function deleteQuantizationDataset(id: number) {
  return apiDelete<boolean>(`/mlops/quantization-datasets/${id}`)
}

export function getQuantizationImages(id: number, params: { page: number; page_size: number }) {
  return apiGet<PaginatedData<QuantizationImageItem>, typeof params>(
    `/mlops/quantization-datasets/${id}/images`,
    params,
  )
}

export async function uploadQuantizationImage(id: number, file: File) {
  const response = await http.post(
    `/mlops/quantization-datasets/${id}/images`,
    file,
    {
      params: { filename: file.name },
      headers: { 'Content-Type': file.type || 'application/octet-stream' },
      timeout: 120000,
    },
  )
  return response.data.data as QuantizationImageUploadResult
}

export async function deleteQuantizationImages(id: number, names: string[]) {
  const response = await http.delete(`/mlops/quantization-datasets/${id}/images`, {
    data: { names },
  })
  return response.data.data as QuantizationDatasetItem
}

function apiAssetUrl(path: string, params?: Record<string, string>) {
  const base = String(http.defaults.baseURL || '').replace(/\/$/, '')
  const query = params ? `?${new URLSearchParams(params).toString()}` : ''
  return `${base}${path}${query}`
}

export function quantizationImageUrl(id: number, filename: string) {
  return apiAssetUrl(`/mlops/quantization-datasets/${id}/images/content`, { filename })
}

export function quantizationImageListUrl(id: number) {
  return apiAssetUrl(`/mlops/quantization-datasets/${id}/ref-img-list`)
}

export async function getQuantizationImageListText(id: number) {
  const response = await http.get<Blob>(
    `/mlops/quantization-datasets/${id}/ref-img-list`,
    { responseType: 'blob' },
  )
  return response.data.text()
}

export function regenerateQuantizationImageList(id: number) {
  return apiPost<QuantizationDatasetItem>(
    `/mlops/quantization-datasets/${id}/ref-img-list/regenerate`,
  )
}
