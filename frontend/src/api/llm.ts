import client from './client'
import type { LLMProviderItem, LLMProviderFormData, LLMTestResult } from '@/types/llm'

export function fetchLLMProviders() {
  return client.get<LLMProviderItem[]>('/api/config/llm')
}

export function createLLMProvider(data: LLMProviderFormData) {
  return client.post<LLMProviderItem>('/api/config/llm', data)
}

export function updateLLMProvider(id: string, data: LLMProviderFormData) {
  return client.put<LLMProviderItem>(`/api/config/llm/${id}`, data)
}

export function deleteLLMProvider(id: string) {
  return client.delete(`/api/config/llm/${id}`)
}

export function testLLMProvider(id: string, message: string) {
  return client.post<LLMTestResult>(`/api/config/llm/${id}/test`, { message })
}

export function testNewLLMProvider(data: LLMProviderFormData & { message: string }) {
  return client.post<LLMTestResult>('/api/config/llm/test', data)
}

export function setPrimaryLLMProvider(id: string) {
  return client.post(`/api/config/llm/${id}/primary`)
}
