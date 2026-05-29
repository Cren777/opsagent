import client from './client'
import type { DiagnosticRunResult, DiagnosticScript } from '@/types/diagnostic'

export function fetchDiagnosticScripts() {
  return client.get<DiagnosticScript[]>('/api/diagnostics/scripts')
}

export function fetchPendingDiagnosticScripts() {
  return client.get<DiagnosticScript[]>('/api/diagnostics/pending')
}

export function uploadDiagnosticScript(file: File) {
  return client.post<DiagnosticScript>('/api/diagnostics/upload', file, {
    params: { filename: file.name },
    headers: { 'Content-Type': 'application/octet-stream' },
  })
}

export function previewDiagnosticScript(scriptName: string, status = 'approved') {
  return client.get<DiagnosticScript>(`/api/diagnostics/scripts/${scriptName}/preview`, {
    params: { status },
  })
}

export function enableDiagnosticScript(scriptName: string) {
  return client.post(`/api/diagnostics/scripts/${scriptName}/enable`)
}

export function disableDiagnosticScript(scriptName: string) {
  return client.post(`/api/diagnostics/scripts/${scriptName}/disable`)
}

export function deleteDiagnosticScript(scriptName: string, status = 'pending') {
  return client.delete<{ deleted: boolean }>(`/api/diagnostics/scripts/${scriptName}`, {
    params: { status },
  })
}

export function runDiagnosticScript(scriptName: string, args: string[] = []) {
  return client.post<DiagnosticRunResult>(`/api/diagnostics/scripts/${scriptName}/run`, { args })
}
