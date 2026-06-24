import { authFetch } from './authFetch'
import client from './client'
import type { ChatRequest, ChatResponse } from '@/types/chat'

export function postChat(data: ChatRequest): Promise<{ data: ChatResponse }> {
  return client.post('/api/chat', data)
}

export function postChatStream(
  data: ChatRequest,
  onToken: (text: string) => void,
  onDone: (meta: { intent?: string; sources?: ChatResponse['sources']; sql?: string | null; diagnostics?: ChatResponse['diagnostics'] }) => void,
  onError: (err: string) => void,
  signal?: AbortSignal
): Promise<void> {
  return authFetch('/api/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
    signal,
  }).then(async (response) => {
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: '流式请求失败' }))
      onError(err.detail || '流式请求失败')
      return
    }

    const reader = response.body?.getReader()
    if (!reader) { onError('无法读取响应流'); return }

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      let eventType = ''
      for (const line of lines) {
        if (line.startsWith('event: ')) {
          eventType = line.slice(7).trim()
        } else if (line.startsWith('data: ')) {
          try {
            const payload = JSON.parse(line.slice(6))
            if (eventType === 'token' && payload.text) {
              onToken(payload.text)
            } else if (eventType === 'done') {
              onDone({
                intent: payload.intent,
                sources: payload.sources,
                sql: payload.sql,
                diagnostics: payload.diagnostics,
              })
            } else if (eventType === 'error') {
              onError(payload.error || '未知错误')
            } else if (eventType === 'intent') {
              // intent event could pass type info early
            }
          } catch { /* skip malformed */ }
        }
      }
    }
  })
}
