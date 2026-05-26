import client from './client'
import type { DiagnosticRunResult, DiagnosticScript } from '@/types/diagnostic'

export function fetchDiagnosticScripts() {
  return client.get<DiagnosticScript[]>('/api/diagnostics/scripts')
}

export function runDiagnosticScript(scriptName: string, args: string[] = []) {
  return client.post<DiagnosticRunResult>(`/api/diagnostics/scripts/${scriptName}/run`, { args })
}
