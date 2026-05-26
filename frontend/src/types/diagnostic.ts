export interface DiagnosticScript {
  name: string
  size: number
  description: string
  timeout: number
}

export interface DiagnosticRunResult {
  stdout: string
  stderr: string
  exit_code: string
}
