export interface ChatAttachment {
  id: string
  type: 'log'
  filename: string
  size?: number
}

export interface ChatHistoryItem {
  role: 'user' | 'assistant'
  content: string
  sql?: string | null
  intent?: string
}

export type SuggestionMode = 'context' | 'completion'

export interface QuestionSuggestionRequest {
  mode: SuggestionMode
  draft: string
  history: ChatHistoryItem[]
  datasource_id?: string
  attachments: ChatAttachment[]
  limit: number
}

export interface QuestionSuggestionResponse {
  mode: SuggestionMode
  source: 'llm' | 'fallback'
  suggestions: string[]
}

export interface ChatRequest {
  query: string
  history?: ChatHistoryItem[]
  datasource_id?: string
  attachments?: ChatAttachment[]
}

export interface ChatResponse {
  answer: string
  intent: string
  sources: { title: string; content: string; score: number }[]
  sql: string | null
  diagnostics?: {
    symptoms?: string[]
    evidence?: string[]
    attachments?: ChatAttachment[]
    case_match?: {
      case_id: string
      score: number
      root_cause?: string
      solution?: string
    } | null
  }
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  intent?: string
  sources?: { title: string; content: string; score: number }[]
  sql?: string | null
  attachments?: ChatAttachment[]
  diagnostics?: ChatResponse['diagnostics']
  timestamp: number
}

export interface ChatSession {
  id: string
  title: string
  messages: ChatMessage[]
  createdAt: number
  updatedAt: number
  pinnedAt?: number
}
