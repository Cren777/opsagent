import { authFetch } from './authFetch'
import type { QuestionSuggestionRequest, QuestionSuggestionResponse } from '@/types/chat'

export async function postQuestionSuggestions(
  data: QuestionSuggestionRequest,
  signal?: AbortSignal,
): Promise<QuestionSuggestionResponse> {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 5000)
  const abort = () => controller.abort()
  if (signal?.aborted) controller.abort()
  else signal?.addEventListener('abort', abort, { once: true })
  try {
    const response = await authFetch('/api/chat/suggestions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
      signal: controller.signal,
    })
    if (!response.ok) throw new Error(`Question suggestions failed: ${response.status}`)
    return await response.json() as QuestionSuggestionResponse
  } finally {
    clearTimeout(timeout)
    signal?.removeEventListener('abort', abort)
  }
}
