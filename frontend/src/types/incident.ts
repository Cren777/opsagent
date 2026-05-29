export interface UploadedLogItem {
  file_id: string
  filename: string
  size: number
  category?: string
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
