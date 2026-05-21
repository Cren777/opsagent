<script setup lang="ts">
import { useChatStore } from '@/stores/chat'
import ChatMessageList from '@/components/chat/ChatMessageList.vue'
import ChatInput from '@/components/chat/ChatInput.vue'

const chatStore = useChatStore()
</script>

<template>
  <div class="chat-view">
    <ChatMessageList />
    <ChatInput />
  </div>
</template>

<style scoped>
.chat-view {
  display: flex;
  flex-direction: column;
  height: 100%;
}
</style>
