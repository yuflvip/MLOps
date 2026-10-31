import { http, apiGet, apiPost } from '../client'
import type { ApiEnvelope, PaginatedData } from '@/shared/types'
export const packagePlatforms = ['x86', '3403', '692', '530', '3588'] as const
export type PackagePlatform = typeof packagePlatforms[number]
export interface PackageInput { exp_id: number; source_file: string; platform: PackagePlatform; runtime?: '3403svp' | '3403nnn'; package_name?: string }
export interface PackagePreview {
  package_name: string; default_package_name: string; platform: string; runtime: string; local_path: string; unpacked_path: string;
  exists: boolean; preview_token: string; cfg_content: string; names_content: string; script: string; files: string[]
}
export interface WeightPackage {
  id: number; package_name: string; project_key: string; project_id: number; exp_name: string; exp_id: number; source_file: string;
  model_type: string | null; training_finished_at: string | null;
  platform: string; runtime: string; model_framework: string; model_size: string | null;
  ftp_uploaded: boolean; ftp_path: string | null; ftp_uploaded_at: string | null;
  created_at: string; size_bytes: number; local_path: string; unpacked_path: string;
  sha256: string; upload_status: string; upload_error: string | null
}
export interface PackageFilters { page?: number; page_size?: number; keyword?: string; platform?: string; uploaded?: boolean; model_type?: string; project_id?: number; upload_status?: string }
export const previewPackage = (input: PackageInput) => apiPost<PackagePreview, PackageInput>('/mlops/weight-packages/preview', input)
export async function createPackage(input: PackageInput & { overwrite: boolean; preview_token: string }) {
  const response = await http.post<ApiEnvelope<WeightPackage>>('/mlops/weight-packages', input, { timeout: 0 })
  return response.data.data
}
export const listPackages = (params: PackageFilters) => apiGet<PaginatedData<WeightPackage>, PackageFilters>('/mlops/weight-packages', params)
export async function uploadPackage(id: number, overwrite: boolean) {
  const response = await http.post<ApiEnvelope<WeightPackage>>(`/mlops/weight-packages/${id}/upload`, { overwrite }, { timeout: 0 })
  return response.data.data
}
export async function downloadPackage(item: WeightPackage) {
  const response = await http.get(`/mlops/weight-packages/${item.id}/download`, { responseType: 'blob' })
  const url = URL.createObjectURL(response.data)
  const link = document.createElement('a'); link.href = url; link.download = item.package_name; link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
