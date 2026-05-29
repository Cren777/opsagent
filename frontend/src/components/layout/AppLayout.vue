<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useChatStore } from '@/stores/chat'
import AppSidebar from './AppSidebar.vue'

const router = useRouter()
const route = useRoute()
const chatStore = useChatStore()

const isSidebarCollapsed = ref(false)

const currentPage = computed(() => {
  const map: Record<string, string> = {
    '/': '智能对话',
    '/knowledge': '知识库管理',
    '/logs-cases': '日志与案例',
    '/diagnostics': '诊断工具',
    '/indexes': '索引管理',
    '/datasources': '数据源配置',
    '/llm': '大模型配置',
  }
  return map[route.path] || 'OpsAgent'
})

function toggleSidebar() {
  isSidebarCollapsed.value = !isSidebarCollapsed.value
}
</script>

<template>
  <div class="app-layout" :class="{ 'sidebar-collapsed': isSidebarCollapsed }">
    <AppSidebar :collapsed="isSidebarCollapsed" @toggle="toggleSidebar" />

    <div class="main-area">
      <header class="app-header">
        <div class="header-left">
          <el-button
            :icon="isSidebarCollapsed ? 'Expand' : 'Fold'"
            text
            @click="toggleSidebar"
          />
          <h1 class="header-title">{{ currentPage }}</h1>
        </div>
        <div class="header-right">
          <el-tag
            :type="chatStore.isStreaming ? 'warning' : chatStore.isLoading ? 'warning' : 'success'"
            size="small"
          >
            {{ chatStore.isStreaming ? '生成中...' : chatStore.isLoading ? '处理中...' : '就绪' }}
          </el-tag>
        </div>
      </header>

      <main class="main-content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background:
    radial-gradient(circle at 12% 0%, rgba(47, 125, 246, 0.12), transparent 34rem),
    linear-gradient(90deg, rgba(16, 22, 38, 0.05), transparent 18rem),
    var(--ops-bg);
}

.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 58px;
  padding: 0 24px;
  background: rgba(248, 250, 252, 0.92);
  border-bottom: 1px solid var(--ops-border);
  box-shadow: 0 1px 10px rgba(16, 24, 40, 0.04);
  backdrop-filter: blur(12px);
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--ops-text);
  margin: 0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.main-content {
  flex: 1;
  overflow: auto;
  background: transparent;
}
</style>
