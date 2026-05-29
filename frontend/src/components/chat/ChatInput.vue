<script setup lang="ts">
import { ref } from 'vue'
import { useChatStore } from '@/stores/chat'
import { ElMessage } from 'element-plus'

const chatStore = useChatStore()
const input = ref('')
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)

function send() {
  const query = input.value.trim() || '请分析上传的日志并给出故障排查建议'
  if ((!input.value.trim() && chatStore.pendingAttachments.length === 0) || chatStore.isLoading) return

  input.value = ''
  chatStore.sendStreamMessage(query)
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}

function openFilePicker() {
  if (!chatStore.isLoading) fileInputRef.value?.click()
}

async function onFileChange(e: Event) {
  const target = e.target as HTMLInputElement
  const files = Array.from(target.files || [])
  target.value = ''
  for (const file of files) {
    try {
      await chatStore.uploadLogAttachment(file)
      ElMessage.success(`${file.name} 已上传`)
    } catch (err) {
      const message = err instanceof Error ? err.message : '上传失败'
      ElMessage.error(message)
    }
  }
}
</script>

<template>
  <div class="chat-input-area">
    <div v-if="chatStore.pendingAttachments.length" class="attachment-row">
      <el-tag
        v-for="item in chatStore.pendingAttachments"
        :key="item.id"
        closable
        type="warning"
        @close="chatStore.removePendingAttachment(item.id)"
      >
        {{ item.filename }}
      </el-tag>
    </div>
    <div class="input-wrapper">
      <input
        ref="fileInputRef"
        class="file-input"
        type="file"
        accept=".log,.txt,.out,.gz"
        multiple
        @change="onFileChange"
      />
      <el-button
        circle
        :icon="'Paperclip'"
        :disabled="chatStore.isLoading"
        @click="openFilePicker"
      />
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
          :disabled="(!input.trim() && chatStore.pendingAttachments.length === 0) || chatStore.isLoading"
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
  background: #fff;
  padding: 12px 14px;
}

.attachment-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}

.file-input {
  display: none;
}

.input-wrapper {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  background: var(--ops-surface-muted);
  border-radius: 10px;
  padding: 10px 12px;
  border: 1px solid var(--ops-border);
  transition: border-color 0.2s ease, background 0.2s ease, box-shadow 0.2s ease;
}

.input-wrapper:focus-within {
  border-color: rgba(47, 125, 246, 0.62);
  background: #fff;
  box-shadow: 0 0 0 3px rgba(47, 125, 246, 0.1);
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
  color: var(--ops-text);
}

.input-textarea::placeholder {
  color: var(--ops-text-muted);
}

.input-actions {
  flex-shrink: 0;
}
</style>
