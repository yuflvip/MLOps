/** User — for future IAM module */
export interface User {
  id: number
  username: string
  display_name: string | null
  email: string | null
  status: string
  created_at: string
  updated_at: string
}

/** Role */
export interface Role {
  id: number
  code: string
  name: string
  description: string | null
}

/** Permission */
export interface Permission {
  id: number
  code: string
  name: string
  module: string
}
