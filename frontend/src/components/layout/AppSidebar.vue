<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'
import SessionList from '@/components/chat/SessionList.vue'

defineProps<{ collapsed: boolean }>()
defineEmits<{ toggle: [] }>()

const router = useRouter()
const route = useRoute()

const navItems = [
  { path: '/', icon: 'ChatDotRound', label: '智能对话' },
  { path: '/knowledge', icon: 'Collection', label: '知识库管理' },
  { path: '/logs-cases', icon: 'Document', label: '日志与案例' },
  { path: '/diagnostics', icon: 'Tools', label: '诊断工具' },
  { path: '/indexes', icon: 'Operation', label: '索引管理' },
  { path: '/datasources', icon: 'Coin', label: '数据源配置' },
  { path: '/llm', icon: 'Cpu', label: '大模型配置' },
]

function navigateTo(path: string) {
  router.push(path)
}
</script>

<template>
  <aside class="app-sidebar" :class="{ collapsed }">
    <div class="sidebar-header">
      <div class="logo">
        <el-icon :size="24"><Monitor /></el-icon>
        <span v-show="!collapsed" class="logo-text">OpsAgent</span>
      </div>
      <el-tag v-show="!collapsed" size="small" type="info">运维客服</el-tag>
    </div>

    <nav class="sidebar-nav">
      <div
        v-for="item in navItems"
        :key="item.path"
        class="nav-item"
        :class="{ active: route.path === item.path }"
        @click="navigateTo(item.path)"
      >
        <el-icon :size="20"><component :is="item.icon" /></el-icon>
        <span v-show="!collapsed" class="nav-label">{{ item.label }}</span>
      </div>
    </nav>

    <SessionList v-show="!collapsed" />
  </aside>
</template>

<style scoped>
.app-sidebar {
  width: 260px;
  background:
    linear-gradient(180deg, rgba(47, 125, 246, 0.08), transparent 220px),
    var(--ops-sidebar);
  color: #fff;
  display: flex;
  flex-direction: column;
  transition: width 0.24s ease;
  flex-shrink: 0;
  overflow: hidden;
  box-shadow: 8px 0 24px rgba(16, 24, 40, 0.12);
}

.app-sidebar.collapsed {
  width: 72px;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 58px;
  padding: 0 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  color: #fff;
}

.logo-text {
  font-size: 18px;
  font-weight: 800;
  letter-spacing: 0;
}

.sidebar-nav {
  padding: 14px 8px 12px;
}

.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 42px;
  padding: 10px 14px;
  border-radius: 8px;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.7);
  transition: background 0.18s ease, color 0.18s ease, transform 0.18s ease;
  margin-bottom: 4px;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}

.nav-item.active {
  background: var(--ops-sidebar-active);
  color: #8fc1ff;
  box-shadow: inset 3px 0 0 var(--ops-primary);
}

.nav-label {
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
}
</style>
