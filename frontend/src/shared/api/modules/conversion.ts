import { apiPostFull } from '../client'
import type { TrainingCreateResult } from './training'

export interface ConversionCreateRequest {
  parent_task_id: number
  task_name?: string | null
  params?: Record<string, unknown>
  execution_params?: Record<string, unknown>
}

export function createOnnxConversion(data: ConversionCreateRequest) {
  return apiPostFull<TrainingCreateResult, ConversionCreateRequest>('/mlops/conversion/onnx', data)
}
