import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import type { ChatMessage, ChatSession } from '@/types/chat'
import { postChat, postChatStream } from '@/api/chat'

const STORAGE_KEY = 'opsagent_sessions'

function loadSessions(): ChatSession[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function saveSessions(sessions: ChatSession[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions))
  } catch {
    // localStorage full or unavailable
  }
}

function generateId(): string {
  return `session-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

function getDefaultTitle(query: string): string {
  const cleaned = query.trim().replace(/[\n\r]+/g, ' ')
  return cleaned.length > 20 ? cleaned.slice(0, 20) + '…' : cleaned
}

export const useChatStore = defineStore('chat', () => {
  // ── State ──
  const sessions = ref<ChatSession[]>(loadSessions())
  const activeSessionId = ref<string | null>(null)
  const isLoading = ref(false)
  const isStreaming = ref(false)
  const selectedDatasourceId = ref<string | null>(null)
  let abortController: AbortController | null = null

  // ── Computed: messages of the active session ──
  const messages = computed<ChatMessage[]>({
    get() {
      const session = sessions.value.find((s) => s.id === activeSessionId.value)
      return session ? session.messages : []
    },
    set(newMessages: ChatMessage[]) {
      const session = sessions.value.find((s) => s.id === activeSessionId.value)
      if (session) {
        session.messages = newMessages
        session.updatedAt = Date.now()
        saveSessions(sessions.value)
      }
    },
  })

  // ── Persist on change ──
  watch(sessions, (val) => saveSessions(val), { deep: true })

  // ── Init: create a session if none exists ──
  const hasActive = activeSessionId.value && sessions.value.find((s) => s.id === activeSessionId.value)
  if (!hasActive) {
    const id = generateId()
    sessions.value.unshift({
      id,
      title: '欢迎',
      messages: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
    })
    activeSessionId.value = id
  }
  // Add welcome message to the active session if it's empty
  const active = sessions.value.find((s) => s.id === activeSessionId.value)
  if (active && active.messages.length === 0) {
    active.messages.push({
      id: 'welcome',
      role: 'assistant',
      content: '你好！我是 OpsAgent 智能运维助手。我可以帮你查询运维知识、分析数据库数据、排查系统故障。请随时输入你的问题。',
      timestamp: Date.now(),
    })
  }

  // ── Internal helpers ──
  function _getSession() {
    return sessions.value.find((s) => s.id === activeSessionId.value)
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

  // ── Public methods ──

  function createSession() {
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
    if (!query.trim() || isLoading.value) return
    const session = _ensureSession(query)
    if (session.title === '新对话' || session.title === '欢迎') {
      session.title = getDefaultTitle(query)
    }

    const userMsg: ChatMessage = { id: `user-${Date.now()}`, role: 'user', content: query, timestamp: Date.now() }
    session.messages.push(userMsg)
    session.updatedAt = Date.now()

    const assistantId = `assistant-${Date.now()}`
    const assistantMsg: ChatMessage = { id: assistantId, role: 'assistant', content: '', timestamp: Date.now() }
    session.messages.push(assistantMsg)

    isLoading.value = true
    try {
      const { data } = await postChat({ query, datasource_id: selectedDatasourceId.value || undefined })
      const idx = session.messages.findIndex((m) => m.id === assistantId)
      if (idx !== -1) {
        session.messages[idx].content = data.answer
        session.messages[idx].intent = data.intent
        session.messages[idx].sources = data.sources
        session.messages[idx].sql = data.sql
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
    if (!query.trim() || isLoading.value) return
    const session = _ensureSession(query)
    if (session.title === '新对话' || session.title === '欢迎') {
      session.title = getDefaultTitle(query)
    }

    const userMsg: ChatMessage = { id: `user-${Date.now()}`, role: 'user', content: query, timestamp: Date.now() }
    session.messages.push(userMsg)
    session.updatedAt = Date.now()

    const assistantId = `assistant-${Date.now()}`
    const assistantMsg: ChatMessage = { id: assistantId, role: 'assistant', content: '', timestamp: Date.now() }
    session.messages.push(assistantMsg)

    isLoading.value = true
    isStreaming.value = true
    abortController = new AbortController()

    await postChatStream(
      { query, datasource_id: selectedDatasourceId.value || undefined },
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

  return {
    sessions,
    activeSessionId,
    messages,
    isLoading,
    isStreaming,
    selectedDatasourceId,
    createSession,
    switchSession,
    deleteSession,
    clearSession,
    sendMessage,
    sendStreamMessage,
    stopStreaming,
  }
})
