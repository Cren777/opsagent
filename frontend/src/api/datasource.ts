import client from './client'
import type { DataSourceItem, DataSourceFormData, ConnectionTestResult } from '@/types/datasource'

export function fetchDataSources() {
  return client.get<DataSourceItem[]>('/api/config/datasources')
}

export function createDataSource(data: DataSourceFormData) {
  return client.post<DataSourceItem>('/api/config/datasources', data)
}

export function updateDataSource(id: string, data: DataSourceFormData) {
  return client.put<DataSourceItem>(`/api/config/datasources/${id}`, data)
}

export function deleteDataSource(id: string) {
  return client.delete(`/api/config/datasources/${id}`)
}

export function testDataSource(id: string) {
  return client.post<ConnectionTestResult>(`/api/config/datasources/${id}/test`)
}

export function testNewDataSource(data: DataSourceFormData) {
  return client.post<ConnectionTestResult>('/api/config/datasources/test', data)
}

export function activateDataSource(id: string) {
  return client.post(`/api/config/datasources/${id}/activate`)
}
