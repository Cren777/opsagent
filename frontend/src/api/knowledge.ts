import client from './client'
import type { KnowledgeFile } from '@/types/knowledge'

export function fetchKnowledgeFiles() {
  return client.get<KnowledgeFile[]>('/api/knowledge/files')
}

export function uploadKnowledgeFile(file: File, relativePath?: string) {
  const filename = relativePath || file.name
  return client.post<KnowledgeFile>(`/api/knowledge/upload?filename=${encodeURIComponent(filename)}`, file, {
    headers: { 'Content-Type': 'application/octet-stream' },
  })
}

export function fetchKnowledgeFile(fileId: string) {
  return client.get<KnowledgeFile>(`/api/knowledge/files/${fileId}`)
}

export function deleteKnowledgeFile(fileId: string) {
  return client.delete<{ deleted: boolean }>(`/api/knowledge/files/${fileId}`)
}

export function rebuildKnowledgeIndex() {
  return client.post('/api/knowledge/reindex')
}
