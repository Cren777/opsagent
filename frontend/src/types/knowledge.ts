export interface KnowledgeFile {
  file_id: string
  filename: string
  relative_path: string
  size: number
  updated_at: string
  indexed: boolean
  content?: string
}
