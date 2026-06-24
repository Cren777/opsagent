import client from './client'
import type {
  IncidentCaseItem,
  IncidentListParams,
  LogCategorySummary,
  LogListParams,
  UploadedLogItem,
} from '@/types/incident'

export function fetchUploadedLogs(params?: LogListParams) {
  return client.get<UploadedLogItem[]>('/api/logs', { params })
}

export function fetchLogCategories() {
  return client.get<LogCategorySummary[]>('/api/logs/categories')
}

export function createLogCategory(name: string) {
  return client.post<LogCategorySummary>('/api/logs/categories', { name })
}

export function renameLogCategory(oldName: string, newName: string) {
  return client.put<LogCategorySummary>('/api/logs/categories/rename', { old_name: oldName, new_name: newName })
}

export function pinLogCategory(name: string, pinned: boolean) {
  return client.put<LogCategorySummary>('/api/logs/categories/pin', { name, pinned })
}

export function deleteLogCategory(name: string) {
  return client.delete<{ deleted: boolean }>('/api/logs/categories', { data: { name } })
}

export function deleteUploadedLog(fileId: string) {
  return client.delete<{ deleted: boolean }>(`/api/logs/${fileId}`)
}

export function previewUploadedLog(fileId: string) {
  return client.get<UploadedLogItem>(`/api/logs/${fileId}/preview`)
}

export function updateUploadedLogCategory(fileId: string, category: string) {
  return client.put<{ updated: boolean }>(`/api/logs/${fileId}/category`, { category })
}

export function fetchIncidentCases(params?: IncidentListParams | string) {
  if (typeof params === 'string') {
    return client.get<IncidentCaseItem[]>('/api/incidents', { params: { status: params || undefined } })
  }
  return client.get<IncidentCaseItem[]>('/api/incidents', { params })
}

export function fetchIncidentCategories() {
  return client.get<LogCategorySummary[]>('/api/incidents/categories')
}

export function createIncidentCategory(name: string) {
  return client.post<LogCategorySummary>('/api/incidents/categories', { name })
}

export function renameIncidentCategory(oldName: string, newName: string) {
  return client.put<LogCategorySummary>('/api/incidents/categories/rename', { old_name: oldName, new_name: newName })
}

export function pinIncidentCategory(name: string, pinned: boolean) {
  return client.put<LogCategorySummary>('/api/incidents/categories/pin', { name, pinned })
}

export function deleteIncidentCategory(name: string) {
  return client.delete<{ deleted: boolean }>('/api/incidents/categories', { data: { name } })
}

export function updateIncidentStatus(caseId: string, status: string) {
  return client.put<{ updated: boolean }>(`/api/incidents/${caseId}/status`, { status })
}

export function fetchIncidentCase(caseId: string) {
  return client.get<IncidentCaseItem>(`/api/incidents/${caseId}`)
}

export function updateIncidentCategory(caseId: string, category: string) {
  return client.put<{ updated: boolean }>(`/api/incidents/${caseId}/category`, { category })
}

export function deleteIncidentCase(caseId: string) {
  return client.delete<{ deleted: boolean }>(`/api/incidents/${caseId}`)
}
