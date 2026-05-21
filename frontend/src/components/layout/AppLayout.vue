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
  background: #f0f2f5;
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
  height: 56px;
  padding: 0 20px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-title {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
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
}

.sidebar-collapsed .app-sidebar {
  /* handled in AppSidebar */
}
</style>
