export type DataSourceType = 'mysql' | 'clickhouse' | 'excel_csv'

export interface MySQLConfig {
  host: string
  port: number
  user: string
  password: string
  database: string
  charset: string
  selected_tables?: string[]
  total_tables?: number
}

export interface ClickHouseConfig {
  host: string
  port: number
  user: string
  password: string
  database: string
  selected_tables?: string[]
  total_tables?: number
}

export interface ExcelCSVConfig {
  file_path: string
  sheet_name: string
}

export type DataSourceConfigDetail = MySQLConfig | ClickHouseConfig | ExcelCSVConfig

export interface DataSourceItem {
  id: string
  name: string
  type: DataSourceType
  is_active: boolean
  config: DataSourceConfigDetail
  created_at: string
  updated_at: string
}

export interface DataSourceFormData {
  name: string
  type: DataSourceType
  config: DataSourceConfigDetail
}

export interface ConnectionTestResult {
  ok: boolean
  message: string
  latency_ms?: number
}
