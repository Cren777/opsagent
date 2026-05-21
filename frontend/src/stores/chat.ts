import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ChatMessage, ChatResponse } from '@/types/chat'
import { postChat, postChatStream } from '@/api/chat'

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([])
  const isLoading = ref(false)
  const isStreaming = ref(false)
  let abortController: AbortController | null = null

  function addMessage(msg: ChatMessage) {
    messages.value.push(msg)
  }

  function clearMessages() {
    messages.value = []
    addSystemWelcome()
  }

  function addSystemWelcome() {
    messages.value.push({
      id: 'welcome',
      role: 'assistant',
      content: '你好！我是 OpsAgent 智能运维助手。我可以帮你查询运维知识、分析数据库数据、排查系统故障。请随时输入你的问题。',
      timestamp: Date.now(),
    })
  }

  async function sendMessage(query: string) {
    if (!query.trim() || isLoading.value) return

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: query,
      timestamp: Date.now(),
    }
    addMessage(userMsg)

    const assistantId = `assistant-${Date.now()}`
    const assistantMsg: ChatMessage = {
      id: assistantId,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
    }
    addMessage(assistantMsg)

    isLoading.value = true

    try {
      const { data } = await postChat({ query })
      const idx = messages.value.findIndex((m) => m.id === assistantId)
      if (idx !== -1) {
        messages.value[idx].content = data.answer
        messages.value[idx].intent = data.intent
        messages.value[idx].sources = data.sources
        messages.value[idx].sql = data.sql
      }
    } catch {
      const idx = messages.value.findIndex((m) => m.id === assistantId)
      if (idx !== -1) {
        messages.value[idx].content = '抱歉，请求失败，请稍后重试。'
      }
    } finally {
      isLoading.value = false
    }
  }

  async function sendStreamMessage(query: string) {
    if (!query.trim() || isLoading.value) return

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: query,
      timestamp: Date.now(),
    }
    addMessage(userMsg)

    const assistantId = `assistant-${Date.now()}`
    const assistantMsg: ChatMessage = {
      id: assistantId,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
    }
    addMessage(assistantMsg)

    isLoading.value = true
    isStreaming.value = true
    abortController = new AbortController()

    await postChatStream(
      { query },
      (token) => {
        const idx = messages.value.findIndex((m) => m.id === assistantId)
        if (idx !== -1) {
          messages.value[idx].content += token
        }
      },
      (meta) => {
        const idx = messages.value.findIndex((m) => m.id === assistantId)
        if (idx !== -1) {
          if (meta.intent) messages.value[idx].intent = meta.intent
          if (meta.sources) messages.value[idx].sources = meta.sources
          if (meta.sql) messages.value[idx].sql = meta.sql
        }
      },
      (err) => {
        const idx = messages.value.findIndex((m) => m.id === assistantId)
        if (idx !== -1 && !messages.value[idx].content) {
          messages.value[idx].content = `错误: ${err}`
        }
      },
      abortController.signal
    ).finally(() => {
      isLoading.value = false
      isStreaming.value = false
      abortController = null
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

  // Initialize with welcome message
  addSystemWelcome()

  return {
    messages,
    isLoading,
    isStreaming,
    sendMessage,
    sendStreamMessage,
    stopStreaming,
    clearMessages,
  }
})
