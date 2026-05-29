<script setup lang="ts">
import { useChatStore } from '@/stores/chat'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

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

async function handleRename(id: string, currentTitle: string) {
  const result = await ElMessageBox.prompt('输入新的会话名称', '重命名会话', {
    inputValue: currentTitle,
    inputPattern: /\S+/,
    inputErrorMessage: '会话名称不能为空',
    confirmButtonText: '保存',
    cancelButtonText: '取消',
  }).catch(() => null)

  if (!result) return
  chatStore.renameSession(id, String(result.value || ''))
  ElMessage.success('会话已重命名')
}

async function handleDelete(id: string) {
  const confirmed = await ElMessageBox.confirm('删除后无法恢复，确认删除此会话？', '删除会话', {
    type: 'warning',
    confirmButtonText: '删除',
    cancelButtonText: '取消',
  }).then(() => true).catch(() => false)

  if (!confirmed) return
  chatStore.deleteSession(id)
}

function handleTogglePin(id: string) {
  chatStore.togglePinSession(id)
}

function handleSessionCommand(command: unknown, id: string, title: string) {
  const action = String(command)
  if (action === 'pin') handleTogglePin(id)
  if (action === 'rename') handleRename(id, title)
  if (action === 'delete') handleDelete(id)
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
        v-for="session in chatStore.displaySessions"
        :key="session.id"
        class="session-item"
        :class="{ active: session.id === chatStore.activeSessionId }"
        @click="handleSwitch(session.id)"
      >
        <div class="session-main">
          <div class="session-title">
            <el-icon v-if="session.pinnedAt" class="pin-icon" :size="13"><Top /></el-icon>
            <span>{{ session.title }}</span>
          </div>
          <div class="session-meta">
            <span class="session-time">{{ formatTime(session.updatedAt) }}</span>
          </div>
        </div>
        <el-dropdown
          class="session-menu"
          trigger="click"
          @command="(command: unknown) => handleSessionCommand(command, session.id, session.title)"
        >
          <el-button
            title="会话操作"
            aria-label="会话操作"
            text
            circle
            size="small"
            :icon="'MoreFilled'"
            @click.stop
          />
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="pin">
                <el-icon><Top /></el-icon>
                {{ session.pinnedAt ? '取消置顶' : '置顶聊天' }}
              </el-dropdown-item>
              <el-dropdown-item command="rename">
                <el-icon><EditPen /></el-icon>
                重命名
              </el-dropdown-item>
              <el-dropdown-item command="delete" divided class="danger-item">
                <el-icon><Delete /></el-icon>
                删除
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>

      <div v-if="chatStore.displaySessions.length === 0" class="empty-hint">
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
  font-size: 12px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.46);
}

.new-btn {
  margin: 0 4px 10px;
  width: calc(100% - 8px);
  justify-content: center;
  border-color: rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.94);
}

.session-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.session-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 10px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s ease;
}

.session-item:hover {
  background: rgba(255, 255, 255, 0.06);
}

.session-item.active {
  background: rgba(47, 125, 246, 0.22);
}

.session-main {
  min-width: 0;
  flex: 1;
}

.session-title {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
  min-width: 0;
}

.session-title span {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.session-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.session-time {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.38);
}

.pin-icon {
  color: #8fc1ff;
  flex: 0 0 auto;
}

.session-menu {
  flex: 0 0 auto;
  opacity: 0;
  transition: opacity 0.15s ease;
}

.session-item:hover .session-menu,
.session-item.active .session-menu {
  opacity: 1;
}

.session-menu :deep(.el-button) {
  color: rgba(255, 255, 255, 0.72);
}

:deep(.danger-item) {
  color: var(--ops-danger);
}

.empty-hint {
  text-align: center;
  color: rgba(255, 255, 255, 0.32);
  font-size: 12px;
  padding: 20px 0;
}
</style>
