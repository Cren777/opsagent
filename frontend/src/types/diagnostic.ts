export interface DiagnosticScript {
  name: string
  size: number
  description: string
  timeout: number
  status?: string
  content?: string
}

export interface DiagnosticRunResult {
  stdout: string
  stderr: string
  exit_code: string
}
