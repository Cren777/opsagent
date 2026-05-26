export interface UploadedLogItem {
  file_id: string
  filename: string
  size: number
  uploaded_at: string
  analysis: {
    line_count: number
    error_count: number
    warning_count: number
    patterns: string[]
    summary: string
  }
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
  created_at: string
  updated_at: string
}
