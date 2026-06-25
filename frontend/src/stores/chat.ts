import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import type { ChatAttachment, ChatHistoryItem, ChatMessage, ChatSession } from '@/types/chat'
import { postChat, postChatStream } from '@/api/chat'
import { uploadLogFile } from '@/api/upload'
import { useAuthStore } from '@/stores/auth'
import { loadUserSessions, saveUserSessions } from '@/stores/chatSessionStorage'

function generateId(): string {
  return `session-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

function getDefaultTitle(query: string): string {
  const cleaned = query.trim().replace(/[\n\r]+/g, ' ')
  return cleaned.length > 20 ? cleaned.slice(0, 20) + '…' : cleaned
}

function hasDiagnosticsPayload(diagnostics: ChatMessage['diagnostics']): boolean {
  return Boolean(
    diagnostics &&
    (diagnostics.case_match || diagnostics.evidence?.length || diagnostics.symptoms?.length)
  )
}

export const useChatStore = defineStore('chat', () => {
  // ── State ──
  const authStore = useAuthStore()
  const sessions = ref<ChatSession[]>([])
  const activeSessionId = ref<string | null>(null)
  const isLoading = ref(false)
  const isStreaming = ref(false)
  const selectedDatasourceId = ref<string | null>(null)
  const pendingAttachments = ref<ChatAttachment[]>([])
  let abortController: AbortController | null = null
  let isHydrating = false

  // ── Computed: messages of the active session ──
  const activeSession = computed<ChatSession | null>(() =>
    sessions.value.find((s) => s.id === activeSessionId.value) || null
  )

  const messages = computed<ChatMessage[]>({
    get() {
      return activeSession.value ? activeSession.value.messages : []
    },
    set(newMessages: ChatMessage[]) {
      const session = activeSession.value
      if (session) {
        session.messages = newMessages
        session.updatedAt = Date.now()
      }
    },
  })

  // ── Computed: only sessions with actual user messages (excludes placeholders) ──
  const displaySessions = computed(() =>
    sessions.value.filter((s) => s.messages.some((m) => m.role === 'user'))
      .sort((left, right) => {
        const pinDiff = (right.pinnedAt || 0) - (left.pinnedAt || 0)
        return pinDiff || right.updatedAt - left.updatedAt
      })
  )

  const requestHistory = computed<ChatHistoryItem[]>(() => (
    activeSession.value ? _buildRequestHistory(activeSession.value) : []
  ))

  // ── Persist on change ──
  watch(sessions, (val) => {
    const userId = authStore.user?.id
    if (!userId || isHydrating) return
    saveUserSessions(localStorage, userId, val)
  }, { deep: true, flush: 'sync' })

  watch(() => authStore.user?.id || null, (userId) => {
    hydrateUserSessions(userId)
  }, { immediate: true })

  // ── Internal helpers ──
  function _getSession() {
    return activeSession.value
  }

  function _ensureSession(query: string) {
    let session = _getSession()
    if (!session) {
      const id = generateId()
      sessions.value.unshift({ id, title: getDefaultTitle(query), messages: [], createdAt: Date.now(), updatedAt: Date.now() })
      activeSessionId.value = id
      session = sessions.value[0]
    }
    return session!
  }

  function _buildRequestHistory(session: ChatSession) {
    return session.messages
      .filter((m) => m.id !== 'welcome' && m.content.trim())
      .slice(-8)
      .map((m) => ({
        role: m.role,
        content: m.content,
        sql: m.sql || undefined,
        intent: m.intent || undefined,
      }))
  }

  function _ensureActiveSession() {
    if (activeSession.value) return
    if (sessions.value.length > 0) {
      activeSessionId.value = sessions.value[0].id
      return
    }
    createSession()
  }

  function hydrateUserSessions(userId: string | null) {
    isHydrating = true
    try {
      if (!userId) {
        sessions.value = []
        activeSessionId.value = null
        return
      }
      sessions.value = loadUserSessions(localStorage, userId)
      activeSessionId.value = null
      _ensureActiveSession()
    } finally {
      isHydrating = false
    }
  }

  function _resetUnauthenticatedSessionState() {
    sessions.value = []
    activeSessionId.value = null
  }

  // ── Public methods ──

  function createSession() {
    if (!authStore.user?.id) {
      _resetUnauthenticatedSessionState()
      return
    }
    const id = generateId()
    const now = Date.now()
    sessions.value.unshift({
      id,
      title: '新对话',
      messages: [{
        id: 'welcome',
        role: 'assistant',
        content: '你好！我是 OpsAgent 智能运维助手。我可以帮你查询运维知识、分析数据库数据、排查系统故障。请随时输入你的问题。',
        timestamp: now,
      }],
      createdAt: now,
      updatedAt: now,
    })
    activeSessionId.value = id
  }

  function switchSession(id: string) {
    if (sessions.value.find((s) => s.id === id)) {
      activeSessionId.value = id
    }
  }

  function deleteSession(id: string) {
    const idx = sessions.value.findIndex((s) => s.id === id)
    if (idx === -1) return
    sessions.value.splice(idx, 1)
    if (activeSessionId.value === id) {
      if (sessions.value.length > 0) {
        activeSessionId.value = sessions.value[0].id
      } else {
        createSession()
      }
    }
  }

  function renameSession(id: string, title: string) {
    const session = sessions.value.find((s) => s.id === id)
    const nextTitle = title.trim()
    if (!session || !nextTitle) return
    session.title = nextTitle.length > 40 ? `${nextTitle.slice(0, 40)}…` : nextTitle
    session.updatedAt = Date.now()
  }

  function togglePinSession(id: string) {
    const session = sessions.value.find((s) => s.id === id)
    if (!session) return
    session.pinnedAt = session.pinnedAt ? undefined : Date.now()
    session.updatedAt = Date.now()
  }

  function clearSession() {
    const session = _getSession()
    if (!session) { createSession(); return }
    session.messages = [{
      id: 'welcome',
      role: 'assistant',
      content: '你好！我是 OpsAgent 智能运维助手。我可以帮你查询运维知识、分析数据库数据、排查系统故障。请随时输入你的问题。',
      timestamp: Date.now(),
    }]
    session.title = '新对话'
    session.updatedAt = Date.now()
  }

  async function sendMessage(query: string) {
    if (!authStore.user?.id) {
      _resetUnauthenticatedSessionState()
      return
    }
    if ((!query.trim() && pendingAttachments.value.length === 0) || isLoading.value) return
    const session = _ensureSession(query)
    if (session.title === '新对话' || session.title === '欢迎') {
      session.title = getDefaultTitle(query)
    }

    const attachments = [...pendingAttachments.value]
    pendingAttachments.value = []
    const userMsg: ChatMessage = { id: `user-${Date.now()}`, role: 'user', content: query, attachments, timestamp: Date.now() }
    session.messages.push(userMsg)
    session.updatedAt = Date.now()

    const assistantId = `assistant-${Date.now()}`
    const assistantMsg: ChatMessage = { id: assistantId, role: 'assistant', content: '', timestamp: Date.now() }
    session.messages.push(assistantMsg)

    isLoading.value = true
    try {
      const { data } = await postChat({
        query,
        history: _buildRequestHistory(session),
        datasource_id: selectedDatasourceId.value || undefined,
        attachments,
      })
      const idx = session.messages.findIndex((m) => m.id === assistantId)
      if (idx !== -1) {
        session.messages[idx].content = data.answer
        session.messages[idx].intent = data.intent
        session.messages[idx].sources = data.sources
        session.messages[idx].sql = data.sql
        if (hasDiagnosticsPayload(data.diagnostics)) {
          session.messages[idx].diagnostics = data.diagnostics
        }
      }
    } catch {
      const idx = session.messages.findIndex((m) => m.id === assistantId)
      if (idx !== -1) session.messages[idx].content = '抱歉，请求失败，请稍后重试。'
    } finally {
      isLoading.value = false
      session.updatedAt = Date.now()
    }
  }

  async function sendStreamMessage(query: string) {
    if (!authStore.user?.id) {
      _resetUnauthenticatedSessionState()
      return
    }
    if ((!query.trim() && pendingAttachments.value.length === 0) || isLoading.value) return
    const session = _ensureSession(query)
    if (session.title === '新对话' || session.title === '欢迎') {
      session.title = getDefaultTitle(query)
    }

    const attachments = [...pendingAttachments.value]
    pendingAttachments.value = []
    const userMsg: ChatMessage = { id: `user-${Date.now()}`, role: 'user', content: query, attachments, timestamp: Date.now() }
    session.messages.push(userMsg)
    session.updatedAt = Date.now()

    const assistantId = `assistant-${Date.now()}`
    const assistantMsg: ChatMessage = { id: assistantId, role: 'assistant', content: '', timestamp: Date.now() }
    session.messages.push(assistantMsg)

    isLoading.value = true
    isStreaming.value = true
    abortController = new AbortController()

    await postChatStream(
      {
        query,
        history: _buildRequestHistory(session),
        datasource_id: selectedDatasourceId.value || undefined,
        attachments,
      },
      (token) => {
        const idx = session.messages.findIndex((m) => m.id === assistantId)
        if (idx !== -1) session.messages[idx].content += token
      },
      (meta) => {
        const idx = session.messages.findIndex((m) => m.id === assistantId)
        if (idx !== -1) {
          if (meta.intent) session.messages[idx].intent = meta.intent
          if (meta.sources) session.messages[idx].sources = meta.sources
          if (meta.sql) session.messages[idx].sql = meta.sql
          if (hasDiagnosticsPayload(meta.diagnostics)) {
            session.messages[idx].diagnostics = meta.diagnostics
          }
        }
      },
      (err) => {
        const idx = session.messages.findIndex((m) => m.id === assistantId)
        if (idx !== -1 && !session.messages[idx].content) {
          session.messages[idx].content = `错误: ${err}`
        }
      },
      abortController.signal
    ).finally(() => {
      isLoading.value = false
      isStreaming.value = false
      abortController = null
      session.updatedAt = Date.now()
    })
  }

  function stopStreaming() {
    if (abortController) {
      abortController.abort()
      abortController = null
      isLoading.value = false
      isStreaming.value = false
    }
  }

  async function uploadLogAttachment(file: File) {
    const { data } = await uploadLogFile(file)
    pendingAttachments.value.push({
      id: data.file_id,
      type: 'log',
      filename: data.filename,
      size: data.size,
    })
  }

  function removePendingAttachment(id: string) {
    pendingAttachments.value = pendingAttachments.value.filter((item) => item.id !== id)
  }

  return {
    sessions,
    displaySessions,
    activeSession,
    activeSessionId,
    messages,
    requestHistory,
    isLoading,
    isStreaming,
    selectedDatasourceId,
    pendingAttachments,
    createSession,
    switchSession,
    deleteSession,
    renameSession,
    togglePinSession,
    clearSession,
    sendMessage,
    sendStreamMessage,
    stopStreaming,
    uploadLogAttachment,
    removePendingAttachment,
  }
})
