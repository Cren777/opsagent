import client from './client'

export interface UploadedLog {
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

export function uploadLogFile(file: File): Promise<{ data: UploadedLog }> {
  return client.post(`/api/uploads/logs?filename=${encodeURIComponent(file.name)}`, file, {
    headers: { 'Content-Type': 'application/octet-stream' },
  })
}
