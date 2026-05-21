<script setup lang="ts">
import { useChatStore } from '@/stores/chat'
import { useRouter } from 'vue-router'

const chatStore = useChatStore()
const router = useRouter()

function formatTime(ts: number): string {
  const d = new Date(ts)
  const now = new Date()
  const isToday = d.toDateString() === now.toDateString()
  if (isToday) {
    return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }
  return `${d.getMonth() + 1}/${d.getDate()} ${d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}`
}

function handleSwitch(id: string) {
  chatStore.switchSession(id)
  router.push('/')
}

function handleNew() {
  chatStore.createSession()
  router.push('/')
}

function handleDelete(e: MouseEvent, id: string) {
  e.stopPropagation()
  chatStore.deleteSession(id)
}
</script>

<template>
  <div class="session-panel">
    <div class="session-header">
      <el-icon :size="14"><Message /></el-icon>
      <span>会话历史</span>
    </div>

    <el-button class="new-btn" size="small" :icon="'Plus'" @click="handleNew">
      新对话
    </el-button>

    <div class="session-list">
      <div
        v-for="session in chatStore.sessions"
        :key="session.id"
        class="session-item"
        :class="{ active: session.id === chatStore.activeSessionId }"
        @click="handleSwitch(session.id)"
      >
        <div class="session-title">{{ session.title }}</div>
        <div class="session-meta">
          <span class="session-time">{{ formatTime(session.updatedAt) }}</span>
          <el-icon
            class="delete-icon"
            :size="14"
            title="删除会话"
            @click="(e: MouseEvent) => handleDelete(e, session.id)"
          >
            <Delete />
          </el-icon>
        </div>
      </div>

      <div v-if="chatStore.sessions.length === 0" class="empty-hint">
        暂无会话记录
      </div>
    </div>
  </div>
</template>

<style scoped>
.session-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 0 8px 12px;
  overflow: hidden;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.session-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 12px 8px 8px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.5);
}

.new-btn {
  margin: 0 4px 8px;
  width: calc(100% - 8px);
  justify-content: center;
}

.session-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.session-item {
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s;
}

.session-item:hover {
  background: rgba(255, 255, 255, 0.06);
}

.session-item.active {
  background: rgba(64, 158, 255, 0.2);
}

.session-title {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.85);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 2px;
}

.session-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.session-time {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.35);
}

.delete-icon {
  color: rgba(255, 255, 255, 0.25);
  cursor: pointer;
  visibility: hidden;
}

.session-item:hover .delete-icon {
  visibility: visible;
}

.delete-icon:hover {
  color: #f56c6c;
}

.empty-hint {
  text-align: center;
  color: rgba(255, 255, 255, 0.3);
  font-size: 12px;
  padding: 20px 0;
}
</style>
