import { apiGet, apiPostFull } from '../client'
import type { PaginationParams, PaginatedData } from '@/shared/types'

// ---------- Types ----------

export interface TrainingTaskSummary {
  id: number
  parent_task_id: number | null
  task_name: string
  task_group: string
  task_type: string
  task_source: string
  status: string
  clearml_task_id: string | null
  queue_name: string | null
  template_name: string | null
  params: Record<string, unknown>
  parameter_snapshot: Record<string, unknown>
  runtime_snapshot: Record<string, unknown>
  custom_data: Record<string, unknown>
  result_summary: Record<string, unknown>
  error_message: string | null
  last_sync_status: string | null
  last_sync_error: string | null
  sync_version: number
  created_at: string
  updated_at: string
}

export interface TrainingCreateMetaTemplate {
  name: string
  display_name: string | null
  queue: string | null
  entrypoint: string | null
  defaults: Record<string, unknown>
  runtime: {
    launcher: string
    script_path: string | null
    working_dir: string | null
    env: Record<string, string>
    artifacts: Array<{
      name: string
      role: string
      format: string
      path: string
    }>
  }
  execution_defaults: Record<string, unknown>
}

export interface TrainingCreateMetaQueue {
  queue_name: string
  agent_count: number
  has_online_agents: boolean
  agents: Array<{ name: string; status: string | null }>
  last_seen: string | null
}

export interface TrainingCreateMetaData {
  templates: TrainingCreateMetaTemplate[]
  queues: TrainingCreateMetaQueue[]
}

export interface TrainingCreateRequest {
  task_name: string
  template_name: string
  params: Record<string, unknown>
  execution_params?: Record<string, unknown>
  queue_name?: string | null
  custom_data?: Record<string, unknown>
}

export interface TrainingCreateSubmission {
  clearml_task_id: string | null
  status: string | null
}

export interface TrainingCreateResult {
  task: TrainingTaskSummary
  submission: TrainingCreateSubmission
}

// ---------- API Calls ----------

export function getTrainingList(params: PaginationParams) {
  return apiGet<PaginatedData<TrainingTaskSummary>, PaginationParams>('/mlops/training', params)
}

export function getTrainingDetail(id: number) {
  return apiGet<TrainingTaskSummary>(`/mlops/training/${id}`)
}

export function getTrainingCreateMeta() {
  return apiGet<TrainingCreateMetaData>('/mlops/training/create-meta')
}

export function createTraining(data: TrainingCreateRequest) {
  return apiPostFull<TrainingCreateResult, TrainingCreateRequest>('/mlops/training', data)
}
