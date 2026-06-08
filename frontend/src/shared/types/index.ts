/** Pagination request params */
export interface PaginationParams {
  page: number
  page_size: number
  status?: string
}

/** Paginated response data wrapper */
export interface PaginatedData<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

/** Generic API success envelope from backend */
export interface ApiEnvelope<T> {
  code: number
  message: string
  data: T
  request_id: string
  warnings: string[]
}

/** API error response */
export interface ApiErrorEnvelope {
  code: number
  message: string
  details: Record<string, unknown>
  request_id: string
}
