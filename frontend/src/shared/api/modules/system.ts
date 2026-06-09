import { apiGet } from '../client'

export interface HealthData {
  status: string
  app_name: string
}

export interface SchedulerStatus {
  enabled: boolean
  running: boolean
  job_count: number
}

export interface RuntimeData {
  scheduler: SchedulerStatus
}

export function getHealth() {
  return apiGet<HealthData>('/mlops/system/health')
}

export function getRuntime() {
  return apiGet<RuntimeData>('/mlops/system/runtime')
}
