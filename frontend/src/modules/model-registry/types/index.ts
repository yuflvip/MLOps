/** Model Family — for future model registry module */
export interface ModelFamily {
  id: number
  code: string
  name: string
  model_type: string | null
  description: string | null
  status: string
  created_at: string
  updated_at: string
}

/** Model Version */
export interface ModelVersion {
  id: number
  model_family_id: number
  version: string
  version_name: string | null
  status: string
  source_task_id: number | null
  description: string | null
  registered_at: string | null
  created_at: string
  updated_at: string
}

/** Model File */
export interface ModelFile {
  id: number
  model_version_id: number | null
  source_task_id: number | null
  parent_model_file_id: number | null
  file_name: string
  file_type: string
  storage_uri: string | null
  framework: string | null
  status: string
  created_at: string
  updated_at: string
}
