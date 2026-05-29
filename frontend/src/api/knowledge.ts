import client from './client'
import type { KnowledgeFile, KnowledgeTreeNode } from '@/types/knowledge'

export function fetchKnowledgeFiles() {
  return client.get<KnowledgeFile[]>('/api/knowledge/files')
}

export function fetchKnowledgeTree() {
  return client.get<KnowledgeTreeNode[]>('/api/knowledge/tree')
}

export function createKnowledgeFolder(path: string) {
  return client.post('/api/knowledge/folders', { path })
}

export function deleteKnowledgeFolder(path: string, recursive = false) {
  return client.delete<{ deleted: boolean }>('/api/knowledge/folders', { params: { path, recursive } })
}

export function renameKnowledgeFolder(path: string, newName: string) {
  return client.put('/api/knowledge/folders/rename', { path, new_name: newName })
}

export function uploadKnowledgeFile(file: File, relativePath?: string, folder?: string) {
  const filename = relativePath || file.name
  return client.post<KnowledgeFile>('/api/knowledge/upload', file, {
    params: { filename, folder: folder || '' },
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
