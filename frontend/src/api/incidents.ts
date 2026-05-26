import client from './client'
import type { IncidentCaseItem, UploadedLogItem } from '@/types/incident'

export function fetchUploadedLogs() {
  return client.get<UploadedLogItem[]>('/api/logs')
}

export function deleteUploadedLog(fileId: string) {
  return client.delete<{ deleted: boolean }>(`/api/logs/${fileId}`)
}

export function fetchIncidentCases(status?: string) {
  return client.get<IncidentCaseItem[]>('/api/incidents', { params: { status: status || undefined } })
}

export function updateIncidentStatus(caseId: string, status: string) {
  return client.put<{ updated: boolean }>(`/api/incidents/${caseId}/status`, { status })
}

export function deleteIncidentCase(caseId: string) {
  return client.delete<{ deleted: boolean }>(`/api/incidents/${caseId}`)
}
