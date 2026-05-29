import client from './client'
import type { IncidentCaseItem, UploadedLogItem } from '@/types/incident'

export function fetchUploadedLogs() {
  return client.get<UploadedLogItem[]>('/api/logs')
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

export function fetchIncidentCases(status?: string) {
  return client.get<IncidentCaseItem[]>('/api/incidents', { params: { status: status || undefined } })
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
