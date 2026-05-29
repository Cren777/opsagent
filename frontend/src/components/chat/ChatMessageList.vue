<script setup lang="ts">
import { ref, watch, nextTick, onBeforeUnmount } from 'vue'
import { useChatStore } from '@/stores/chat'
import ChatMessage from './ChatMessage.vue'

const chatStore = useChatStore()
const listRef = ref<HTMLElement | null>(null)
const autoScroll = ref(true)
let streamingTimer: number | undefined

watch(
  () => chatStore.messages.length,
  () => {
    autoScroll.value = true
    nextTick(() => scrollToBottom())
  }
)

watch(
  () => chatStore.isStreaming,
  (streaming) => {
    if (streaming) {
      streamingTimer = window.setInterval(() => {
        if (autoScroll.value) scrollToBottom()
      }, 100)
    } else if (streamingTimer) {
      clearInterval(streamingTimer)
      streamingTimer = undefined
    }
  }
)

function handleScroll() {
  const el = listRef.value
  if (!el) return
  const distanceToBottom = el.scrollHeight - el.scrollTop - el.clientHeight
  autoScroll.value = distanceToBottom < 80
}

function scrollToBottom() {
  if (listRef.value) {
    listRef.value.scrollTop = listRef.value.scrollHeight
  }
}

onBeforeUnmount(() => {
  if (streamingTimer) clearInterval(streamingTimer)
})
</script>

<template>
  <div ref="listRef" class="message-list" @scroll="handleScroll">
    <div v-if="chatStore.messages.length === 0" class="empty-state">
      <el-empty description="输入问题开始对话" :image-size="120" />
    </div>

    <ChatMessage
      v-for="msg in chatStore.messages"
      :key="msg.id"
      :message="msg"
    />
  </div>
</template>

<style scoped>
.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 18px 0 22px;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--ops-text-muted);
}
</style>
