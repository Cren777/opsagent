export interface UploadedLogItem {
  file_id: string
  filename: string
  size: number
  source?: 'uploaded' | 'runtime' | 'seed' | 'local' | string
  category?: string
  severity?: 'error' | 'warning' | 'info' | string
  tags?: string[]
  stored_path?: string
  updated_at?: string
  mtime?: number
  uploaded_at: string
  analysis: {
    line_count: number
    error_count: number
    warning_count: number
    patterns: string[]
    summary: string
  }
  content?: string
}

export interface IncidentCaseItem {
  case_id: string
  query: string
  answer: string
  symptoms: string[]
  root_cause: string
  solution: string
  evidence: string[]
  status: string
  category?: string
  created_at: string
  updated_at: string
}

export interface LogCategorySummary {
  name: string
  count: number
  error_count: number
  warning_count: number
  pinned?: boolean
  user_defined?: boolean
}

export interface LogListParams {
  query?: string
  category?: string
  source?: string
  severity?: string
}

export interface IncidentListParams {
  query?: string
  category?: string
  status?: string
  symptom?: string
}
