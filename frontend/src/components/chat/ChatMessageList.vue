<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { useChatStore } from '@/stores/chat'
import ChatMessage from './ChatMessage.vue'

const chatStore = useChatStore()
const listRef = ref<HTMLElement | null>(null)

watch(
  () => chatStore.messages.length,
  () => {
    nextTick(() => scrollToBottom())
  }
)

watch(
  () => chatStore.isStreaming,
  (streaming) => {
    if (streaming) {
      const timer = setInterval(() => {
        scrollToBottom()
      }, 100)
      watch(
        () => chatStore.isStreaming,
        (v) => {
          if (!v) clearInterval(timer)
        }
      )
    }
  }
)

function scrollToBottom() {
  if (listRef.value) {
    listRef.value.scrollTop = listRef.value.scrollHeight
  }
}
</script>

<template>
  <div ref="listRef" class="message-list">
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
  padding: 16px 0;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}
</style>
