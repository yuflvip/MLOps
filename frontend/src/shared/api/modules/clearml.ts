import { apiGet } from '../client'

// ---------- Types ----------

export interface TaskLogEvent {
  timestamp: number
  level: string
  msg: string
  worker: string
  type?: string
  task?: string
}

export interface TaskLogData {
  events: TaskLogEvent[]
  returned: number
  total: number
}

// ---------- API Calls ----------

export interface GetTaskLogParams {
  task: string
  batch_size?: number
  from_timestamp?: number | null
  order?: 'asc' | 'desc'
}

/** GET /mlops/clearml/events/get_task_log — proxy to ClearML events.get_task_log */
export function getTaskLog(params: GetTaskLogParams) {
  const query: Record<string, unknown> = { task: params.task }
  if (params.batch_size !== undefined) query.batch_size = params.batch_size
  if (params.from_timestamp != null) query.from_timestamp = params.from_timestamp
  if (params.order) query.order = params.order
  return apiGet<TaskLogData>('/mlops/clearml/events/get_task_log', query)
}
