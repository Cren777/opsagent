export type SuggestionMode = 'context' | 'completion'

export interface SuggestionCacheKeyInput {
  userId: string
  sessionId: string
  datasourceId?: string | null
  attachmentIds?: string[]
  mode: SuggestionMode
  draft?: string
  contextId?: string
}

export interface FrontendFallbackInput {
  mode: SuggestionMode
  draft: string
  hasDatasource: boolean
  hasLogAttachment: boolean
  limit: number
}

interface CacheEntry {
  suggestions: string[]
  createdAt: number
}

const DRAFT_PREVIEW_MAX_LENGTH = 44

const PRIMARY_LOG_SUGGESTIONS = [
  '\u8fd9\u4efd\u65e5\u5fd7\u91cc\u6700\u53ef\u80fd\u7684\u6545\u969c\u539f\u56e0\u662f\u4ec0\u4e48\uff1f',
  '\u8bf7\u6309\u65f6\u95f4\u7ebf\u603b\u7ed3\u65e5\u5fd7\u4e2d\u7684\u5f02\u5e38\u4e8b\u4ef6',
]

const SECONDARY_LOG_SUGGESTIONS = [
  '\u54ea\u4e9b\u9519\u8bef\u9700\u8981\u4f18\u5148\u6392\u67e5\uff1f',
]

const PRIMARY_DATASOURCE_SUGGESTIONS = [
  '\u57fa\u4e8e\u5f53\u524d\u6570\u636e\u6e90\uff0c\u5e2e\u6211\u5206\u6790\u5173\u952e\u6307\u6807\u8d8b\u52bf',
  '\u67e5\u8be2\u6700\u8fd1\u7684\u5f02\u5e38\u6570\u636e\u6709\u54ea\u4e9b\uff1f',
]

const SECONDARY_DATASOURCE_SUGGESTIONS = [
  '\u5e2e\u6211\u751f\u6210\u4e00\u6761\u5b89\u5168\u7684\u67e5\u8be2\u8bed\u53e5',
]

const GENERAL_SUGGESTIONS = [
  '\u5f53\u524d\u7cfb\u7edf\u6709\u54ea\u4e9b\u9700\u8981\u5173\u6ce8\u7684\u98ce\u9669\uff1f',
  '\u5e2e\u6211\u751f\u6210\u4e00\u4efd\u6545\u969c\u6392\u67e5\u6e05\u5355',
  '\u603b\u7ed3\u4e00\u4e0b\u4e0b\u4e00\u6b65\u8fd0\u7ef4\u52a8\u4f5c',
]

export class SuggestionMemoryCache {
  private readonly ttlMs: number
  private readonly maxEntries: number
  private readonly entries = new Map<string, CacheEntry>()

  constructor(options: { ttlMs: number; maxEntries: number }) {
    this.ttlMs = Math.max(0, options.ttlMs)
    this.maxEntries = Math.max(0, options.maxEntries)
  }

  get(key: string): string[] | undefined {
    const entry = this.entries.get(key)
    if (!entry) {
      return undefined
    }

    if (Date.now() - entry.createdAt >= this.ttlMs) {
      this.entries.delete(key)
      return undefined
    }

    return [...entry.suggestions]
  }

  set(key: string, suggestions: string[]): void {
    if (this.maxEntries === 0) {
      return
    }

    if (this.entries.has(key)) {
      this.entries.delete(key)
    }

    this.entries.set(key, {
      suggestions: [...suggestions],
      createdAt: Date.now(),
    })

    while (this.entries.size > this.maxEntries) {
      const oldestKey = this.entries.keys().next().value
      if (oldestKey === undefined) {
        break
      }
      this.entries.delete(oldestKey)
    }
  }

  clear(): void {
    this.entries.clear()
  }
}

export class LatestSuggestionRequest {
  private controller?: AbortController
  private requestId = 0

  async run<T>(requester: (signal: AbortSignal) => Promise<T>): Promise<T | undefined> {
    this.cancel()

    const controller = new AbortController()
    const currentRequestId = this.requestId + 1
    this.requestId = currentRequestId
    this.controller = controller

    try {
      const result = await requester(controller.signal)
      if (this.requestId !== currentRequestId || controller.signal.aborted) {
        return undefined
      }
      return result
    } catch (error) {
      if (isAbortError(error) || this.requestId !== currentRequestId) {
        return undefined
      }
      throw error
    } finally {
      if (this.requestId === currentRequestId) {
        this.controller = undefined
      }
    }
  }

  cancel(): void {
    if (this.controller) {
      this.controller.abort()
      this.controller = undefined
    }
  }
}

export function buildSuggestionCacheKey(input: SuggestionCacheKeyInput): string {
  const parts = [
    input.userId,
    input.sessionId,
    input.datasourceId ?? '',
    [...(input.attachmentIds ?? [])].sort(),
    input.mode,
    normalizeDraft(input.draft ?? ''),
    input.contextId ?? '',
  ]

  return JSON.stringify(parts)
}

export function buildFrontendFallback(input: FrontendFallbackInput): string[] {
  if (input.limit <= 0) {
    return []
  }

  const suggestions: string[] = []
  const normalizedDraft = normalizeDraft(input.draft)

  if (input.mode === 'completion' && normalizedDraft.length > 0) {
    suggestions.push(`\u7ee7\u7eed\u5b8c\u5584\uff1a${truncateDraft(normalizedDraft)}`)
  }

  if (input.hasLogAttachment) {
    suggestions.push(...PRIMARY_LOG_SUGGESTIONS)
  }

  if (input.hasDatasource) {
    suggestions.push(...PRIMARY_DATASOURCE_SUGGESTIONS)
  }

  suggestions.push(...GENERAL_SUGGESTIONS)

  if (input.hasLogAttachment) {
    suggestions.push(...SECONDARY_LOG_SUGGESTIONS)
  }

  if (input.hasDatasource) {
    suggestions.push(...SECONDARY_DATASOURCE_SUGGESTIONS)
  }

  return dedupe(suggestions).slice(0, input.limit)
}

function normalizeDraft(draft: string): string {
  return draft.trim().replace(/\s+/g, ' ')
}

function truncateDraft(draft: string): string {
  if (draft.length <= DRAFT_PREVIEW_MAX_LENGTH) {
    return draft
  }
  return `${draft.slice(0, DRAFT_PREVIEW_MAX_LENGTH)}...`
}

function dedupe(values: string[]): string[] {
  const seen = new Set<string>()
  const result: string[] = []

  for (const value of values) {
    const normalized = value.trim()
    if (!normalized || seen.has(normalized)) {
      continue
    }
    seen.add(normalized)
    result.push(normalized)
  }

  return result
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError'
    || error instanceof Error && error.name === 'AbortError'
}
