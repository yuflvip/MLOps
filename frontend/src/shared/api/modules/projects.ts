import { apiDelete, apiGet, apiPost, apiPut } from '../client'
import type { PaginatedData } from '@/shared/types'

export interface ProjectItem {
  id: number
  project: string
  name: string
  model_type: string | null
  model_architecture: string | null
  description: string | null
  exp_root_path: string | null
  dataset_ids: number[]
  epochs: number | null
  batch: number | null
  imgsz: number | null
  created_at: string
  updated_at: string
}

export interface ProjectListParams {
  page?: number
  page_size?: number
  project?: string
  name?: string
  model_type?: string
}

export interface ProjectFormPayload {
  project: string
  name: string
  model_type: string
  model_architecture: string
  description?: string | null
  exp_root_path: string
  dataset_ids: number[]
  epochs?: number | null
  batch?: number | null
  imgsz?: number | null
}

export function getProjectList(params?: ProjectListParams) {
  return apiGet<PaginatedData<ProjectItem>, ProjectListParams>('/mlops/projects', params)
}

export function getProjectDetail(id: number) {
  return apiGet<ProjectItem>(`/mlops/projects/${id}`)
}

export function createProject(data: ProjectFormPayload) {
  return apiPost<ProjectItem, ProjectFormPayload>('/mlops/projects', data)
}

export function updateProject(id: number, data: ProjectFormPayload) {
  return apiPut<ProjectItem, ProjectFormPayload>(`/mlops/projects/${id}`, data)
}

export function deleteProject(id: number) {
  return apiDelete<boolean>(`/mlops/projects/${id}`)
}
