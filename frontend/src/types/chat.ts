export interface ChatRequest {
  query: string
  history?: { role: string; content: string }[]
  datasource_id?: string
}

export interface ChatResponse {
  answer: string
  intent: string
  sources: { title: string; content: string; score: number }[]
  sql: string | null
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  intent?: string
  sources?: { title: string; content: string; score: number }[]
  sql?: string | null
  timestamp: number
}

export interface ChatSession {
  id: string
  title: string
  messages: ChatMessage[]
  createdAt: number
  updatedAt: number
}
