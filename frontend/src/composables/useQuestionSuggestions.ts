import { onScopeDispose, ref, watch, type ComputedRef, type Ref } from 'vue'
import { postQuestionSuggestions } from '@/api/chatSuggestions'
import type { ChatAttachment, ChatHistoryItem } from '@/types/chat'
import {
  LatestSuggestionRequest,
  SuggestionMemoryCache,
  buildFrontendFallback,
  buildSuggestionCacheKey,
  type SuggestionMode,
} from './questionSuggestionsCore'

type ReadableRef<T> = Ref<T> | ComputedRef<T>

export interface QuestionSuggestionOptions {
  draft: Ref<string>
  userId: ReadableRef<string>
  sessionId: ReadableRef<string>
  contextVersion: ReadableRef<string>
  history: ReadableRef<ChatHistoryItem[]>
  datasourceId: ReadableRef<string | null>
  attachments: ReadableRef<ChatAttachment[]>
  isStreaming: ReadableRef<boolean>
}

export function useQuestionSuggestions(options: QuestionSuggestionOptions): {
  suggestions: Ref<string[]>
  isLoading: Ref<boolean>
  refresh: (force?: boolean) => Promise<void>
} {
  const cache = new SuggestionMemoryCache({ ttlMs: 60_000, maxEntries: 30 })
  const runner = new LatestSuggestionRequest()
  const suggestions = ref<string[]>([])
  const contextSuggestions = ref<string[]>([])
  const isLoading = ref(false)
  let debounceTimer: number | undefined
  let refreshVersion = 0

  async function refresh(force = false): Promise<void> {
    const userId = options.userId.value
    const sessionId = options.sessionId.value

    if (options.isStreaming.value || !userId || !sessionId) {
      runner.cancel()
      isLoading.value = false
      if (!userId || !sessionId) suggestions.value = []
      return
    }

    const normalizedDraft = options.draft.value.trim()
    if (normalizedDraft.length === 1) {
      runner.cancel()
      suggestions.value = [...contextSuggestions.value]
      return
    }

    const mode: SuggestionMode = normalizedDraft ? 'completion' : 'context'
    const attachmentIds = options.attachments.value.map((item) => item.id)
    const key = buildSuggestionCacheKey({
      userId,
      sessionId,
      datasourceId: options.datasourceId.value,
      attachmentIds,
      mode,
      draft: normalizedDraft,
      contextId: options.contextVersion.value,
    })

    const fallback = buildFrontendFallback({
      mode,
      draft: normalizedDraft,
      hasDatasource: Boolean(options.datasourceId.value),
      hasLogAttachment: options.attachments.value.some((item) => item.type === 'log'),
      limit: 6,
    })

    const cached = force ? undefined : cache.get(key)
    if (cached) {
      suggestions.value = cached
      if (mode === 'context') contextSuggestions.value = cached
      return
    }

    const currentVersion = ++refreshVersion
    isLoading.value = true
    try {
      const result = await runner.run((signal) => postQuestionSuggestions({
        mode,
        draft: mode === 'completion' ? normalizedDraft : '',
        history: options.history.value.slice(-8),
        datasource_id: options.datasourceId.value || undefined,
        attachments: options.attachments.value,
        limit: 6,
      }, signal))

      if (!result) return
      const next = result.suggestions.length ? result.suggestions : fallback
      cache.set(key, next)
      suggestions.value = next
      if (mode === 'context') contextSuggestions.value = next
    } catch {
      suggestions.value = fallback
      if (mode === 'context') contextSuggestions.value = fallback
    } finally {
      if (currentVersion === refreshVersion) {
        isLoading.value = false
      }
    }
  }

  function scheduleRefresh(): void {
    window.clearTimeout(debounceTimer)
    const normalizedDraft = options.draft.value.trim()

    if (normalizedDraft.length === 1) {
      runner.cancel()
      suggestions.value = [...contextSuggestions.value]
      return
    }

    if (normalizedDraft) {
      debounceTimer = window.setTimeout(() => { void refresh() }, 500)
    } else {
      void refresh()
    }
  }

  watch(options.userId, () => {
    cache.clear()
    runner.cancel()
    suggestions.value = []
    contextSuggestions.value = []
  })

  watch(
    [
      options.draft,
      options.userId,
      options.sessionId,
      options.contextVersion,
      options.datasourceId,
      options.attachments,
    ],
    scheduleRefresh,
    { deep: true, immediate: true },
  )

  watch(options.isStreaming, (streaming, wasStreaming) => {
    if (streaming) runner.cancel()
    if (wasStreaming && !streaming && !options.draft.value.trim()) void refresh(true)
  })

  onScopeDispose(() => {
    window.clearTimeout(debounceTimer)
    runner.cancel()
    cache.clear()
  })

  return { suggestions, isLoading, refresh }
}