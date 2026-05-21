export interface LLMProviderItem {
  id: string
  name: string
  provider_type: string
  base_url: string
  model: string
  temperature: number
  max_tokens: number
  is_primary: boolean
  created_at: string
  updated_at: string
}

export interface LLMProviderFormData {
  name: string
  provider_type: string
  api_key: string
  base_url: string
  model: string
  temperature: number
  max_tokens: number
  is_primary: boolean
}

export interface LLMTestResult {
  response: string
  latency_ms: number
}
