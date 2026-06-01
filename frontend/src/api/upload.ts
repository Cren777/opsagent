import client from './client'

export interface UploadedLog {
  file_id: string
  filename: string
  size: number
  source?: string
  category?: string
  severity?: string
  uploaded_at: string
  analysis: {
    line_count: number
    error_count: number
    warning_count: number
    patterns: string[]
    summary: string
  }
}

export function uploadLogFile(
  file: File,
  options: { category?: string } = {}
): Promise<{ data: UploadedLog }> {
  const params = new URLSearchParams({ filename: file.name })
  if (options.category) params.set('category', options.category)
  return client.post(`/api/uploads/logs?${params.toString()}`, file, {
    headers: { 'Content-Type': 'application/octet-stream' },
  })
}
