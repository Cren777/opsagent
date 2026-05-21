<script setup lang="ts">
import { ref } from 'vue'
import { useChatStore } from '@/stores/chat'

const chatStore = useChatStore()
const input = ref('')
const textareaRef = ref<HTMLTextAreaElement | null>(null)

function send() {
  const query = input.value.trim()
  if (!query || chatStore.isLoading) return

  input.value = ''
  chatStore.sendStreamMessage(query)
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}
</script>

<template>
  <div class="chat-input-area">
    <div class="input-wrapper">
      <textarea
        ref="textareaRef"
        v-model="input"
        class="input-textarea"
        placeholder="输入你的问题... (Enter 发送, Shift+Enter 换行)"
        rows="1"
        :disabled="chatStore.isLoading"
        @keydown="onKeydown"
        @input="
          const el = $event.target as HTMLTextAreaElement;
          el.style.height = 'auto';
          el.style.height = Math.min(el.scrollHeight, 150) + 'px';
        "
      />
      <div class="input-actions">
        <el-button
          v-if="!chatStore.isStreaming"
          type="primary"
          :icon="'Promotion'"
          :disabled="!input.trim() || chatStore.isLoading"
          @click="send"
        >
          发送
        </el-button>
        <el-button
          v-else
          type="danger"
          :icon="'Close'"
          @click="chatStore.stopStreaming()"
        >
          停止生成
        </el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-input-area {
  border-top: 1px solid #e4e7ed;
  background: #fff;
  padding: 16px 20px;
}

.input-wrapper {
  max-width: 900px;
  margin: 0 auto;
  display: flex;
  align-items: flex-end;
  gap: 12px;
  background: #f5f7fa;
  border-radius: 12px;
  padding: 10px 14px;
  border: 1px solid #e4e7ed;
  transition: border-color 0.2s;
}

.input-wrapper:focus-within {
  border-color: #409eff;
  background: #fff;
}

.input-textarea {
  flex: 1;
  border: none;
  outline: none;
  resize: none;
  font-size: 14px;
  line-height: 1.6;
  background: transparent;
  font-family: inherit;
  max-height: 150px;
}

.input-textarea::placeholder {
  color: #c0c4cc;
}

.input-actions {
  flex-shrink: 0;
}
</style>
