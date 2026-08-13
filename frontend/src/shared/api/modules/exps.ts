import { apiDelete, apiGet, apiPost, http } from '../client'
import type { PaginatedData } from '@/shared/types'

export type ExpReviewStatus = 'pending_review' | 'approved' | 'rejected'

export interface ExpItem {
  id: number
  project_id: number
  name: string
  relative_path: string
  resolved_path: string
  review_status: ExpReviewStatus
  version: string | null
  description: string | null
  review_comment: string | null
  training_started_at: string | null
  training_finished_at: string | null
  validation_metric_value: number | null
  imported_at: string
  reviewed_at: string | null
  created_at: string
  updated_at: string
}

export interface ExpListParams {
  page?: number
  page_size?: number
  project_id?: number
  review_status?: ExpReviewStatus
  model_type?: string
}

export interface ExpCandidate {
  name: string
  relative_path: string
  modified_at: string
  already_imported: boolean
}

export interface ExpCandidateListData {
  project_id: number
  exp_root_path: string
  items: ExpCandidate[]
}

export type ExpArtifactPreviewKind =
  | 'image'
  | 'pdf'
  | 'json'
  | 'text'
  | 'table'
  | 'xlsx'
  | 'binary'
  | 'unsupported'

export interface ExpArtifactItem {
  name: string
  relative_path: string
  extension: string
  media_type: string
  size_bytes: number
  modified_at: string
  preview_kind: ExpArtifactPreviewKind
}

export interface ExpModelArtifactItem extends ExpArtifactItem {
  md5: string
}

export interface ExpArtifactPreviewData {
  relative_path: string
  preview_kind: ExpArtifactPreviewKind
  content: string | null
  columns: string[]
  rows: unknown[][]
  sheet_names: string[]
  sheet_name: string | null
  page: number
  page_size: number
  has_more: boolean
  truncated: boolean
}

export type ModelConversionStatus = 'queued' | 'running' | 'succeeded' | 'failed'

export interface ModelConversionItem {
  id: number
  exp_id: number
  parent_conversion_id: number | null
  converter_code: string
  source_file: string
  source_format: string
  target_platform: string
  target_format: string
  output_file: string
  status: ModelConversionStatus
  params: {
    device?: string
    imgsz?: string
    opset?: number
    simplify?: boolean
    dynamo?: boolean
    overwrite?: boolean
    quantization_dataset_id?: number
    quantization_dataset_name?: string
    image_list_path?: string
    input_shape?: string
    insert_op_conf?: string
    soc_version?: string
    compile_mode?: string
    output_type?: string
    quant_mode?: string
    high_precision_layer?: string
    online_model_type?: string
    weight_quant_per_channel?: number
    matmul_per_channel_enable?: number
    all_batch_quant_together_enable?: number
    softmax_optimize_enable?: number
    dry_run?: boolean
    enable_single_stream?: boolean
    enable_small_channel?: number
  }
  result_files: string[]
  log_path: string | null
  error_message: string | null
  created_at: string
  started_at: string | null
  finished_at: string | null
}

export interface OnnxConversionCreatePayload {
  converter_code: 'hgnet_to_onnx'
  source_file: string
  output_file: string
  params: {
    device: 'cpu' | 'cuda'
    imgsz: string
    opset: number
    simplify: boolean
    dynamo: boolean
    overwrite: boolean
  }
}

export interface Hisi3403ConversionCreatePayload {
  converter_code: 'onnx_to_hisi3403'
  source_file: string
  output_file: string
  params: {
    quantization_dataset_id: number
    input_shape: string
    insert_op_conf: 'insert_op.cfg' | 'insert_op_hgnet.cfg'
    soc_version: string
    compile_mode: string
    output_type: string
    quant_mode: string
    high_precision_layer: string
    online_model_type: string
    weight_quant_per_channel: 0 | 1
    matmul_per_channel_enable: 0 | 1
    all_batch_quant_together_enable: 0 | 1
    softmax_optimize_enable: 0 | 1
    dry_run: boolean
    overwrite: boolean
  }
}

export interface Hisi3403AscendNnnConversionCreatePayload {
  converter_code: 'onnx_to_hisi3403_ascend_nnn'
  source_file: string
  output_file: string
  params: {
    input_shape: string
    insert_op_conf: 'insert_op_nnn_hgnet.cfg'
    soc_version: string
    enable_single_stream: boolean
    enable_small_channel: 0 | 1
    dry_run: boolean
    overwrite: boolean
  }
}

export type ModelConversionCreatePayload =
  | OnnxConversionCreatePayload
  | Hisi3403ConversionCreatePayload
  | Hisi3403AscendNnnConversionCreatePayload

export function getExpList(params?: ExpListParams) {
  return apiGet<PaginatedData<ExpItem>, ExpListParams>('/mlops/exps', params)
}

export function getExpDetail(id: number) {
  return apiGet<ExpItem>(`/mlops/exps/${id}`)
}

export function getExpArtifacts(id: number) {
  return apiGet<{ items: ExpArtifactItem[]; total: number }>(`/mlops/exps/${id}/artifacts`)
}

export function getExpModelArtifacts(id: number) {
  return apiGet<{ items: ExpModelArtifactItem[]; total: number }>(
    `/mlops/exps/${id}/model-artifacts`,
  )
}

export function getExpArtifactPreview(
  id: number,
  params: {
    path: string
    page?: number
    page_size?: number
    sheet_name?: string
    tail?: boolean
  },
) {
  return apiGet<ExpArtifactPreviewData, typeof params>(`/mlops/exps/${id}/artifacts/preview`, params)
}

export async function getExpArtifactBlob(id: number, path: string) {
  const response = await http.get<Blob>(`/mlops/exps/${id}/artifacts/content`, {
    params: { path },
    responseType: 'blob',
  })
  return response.data
}

export function getExpCandidates(projectId: number) {
  return apiGet<ExpCandidateListData>(`/mlops/projects/${projectId}/exp-candidates`)
}

export function createModelConversion(expId: number, data: ModelConversionCreatePayload) {
  return apiPost<ModelConversionItem, ModelConversionCreatePayload>(
    `/mlops/exps/${expId}/conversions`,
    data,
  )
}

export function getModelConversions(expId: number) {
  return apiGet<{ items: ModelConversionItem[]; total: number }>(
    `/mlops/exps/${expId}/conversions`,
  )
}

export function importExps(projectId: number, relativePaths: string[]) {
  return apiPost<ExpItem[], { relative_paths: string[] }>(
    `/mlops/projects/${projectId}/exps/import`,
    { relative_paths: relativePaths },
  )
}

export function approveExp(id: number, data: { version: string; description?: string | null }) {
  return apiPost<ExpItem, { version: string; description?: string | null }>(
    `/mlops/exps/${id}/approve`,
    data,
  )
}

export function rejectExp(id: number, reviewComment: string) {
  return apiPost<ExpItem, { review_comment: string }>(`/mlops/exps/${id}/reject`, {
    review_comment: reviewComment,
  })
}

export function deleteExp(id: number) {
  return apiDelete<boolean>(`/mlops/exps/${id}`)
}
