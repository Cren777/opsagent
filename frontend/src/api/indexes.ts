import client from './client'
import type { IndexStatus } from '@/types/indexes'

export function fetchIndexStatus() {
  return client.get<IndexStatus>('/api/indexes/status')
}

export function rebuildKnowledgeIndex() {
  return client.post('/api/indexes/knowledge/rebuild')
}

export function rebuildLogIndex(path?: string) {
  return client.post('/api/indexes/logs/rebuild', { path: path || null })
}

export function rebuildCaseIndex() {
  return client.post('/api/indexes/cases/rebuild')
}

export function clearIndexCollection(collection: string) {
  return client.post(`/api/indexes/${encodeURIComponent(collection)}/clear`)
}
