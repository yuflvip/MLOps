import { apiGet, apiPost, http } from '../client'
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

export function getExpList(params?: ExpListParams) {
  return apiGet<PaginatedData<ExpItem>, ExpListParams>('/mlops/exps', params)
}

export function getExpDetail(id: number) {
  return apiGet<ExpItem>(`/mlops/exps/${id}`)
}

export function getExpArtifacts(id: number) {
  return apiGet<{ items: ExpArtifactItem[]; total: number }>(`/mlops/exps/${id}/artifacts`)
}

export function getExpArtifactPreview(
  id: number,
  params: { path: string; page?: number; page_size?: number; sheet_name?: string },
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
