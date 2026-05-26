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
  background: #1a1a2e;
  color: #fff;
  display: flex;
  flex-direction: column;
  transition: width 0.3s;
  flex-shrink: 0;
  overflow: hidden;
}

.app-sidebar.collapsed {
  width: 64px;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #fff;
}

.logo-text {
  font-size: 18px;
  font-weight: 700;
  letter-spacing: 1px;
}

.sidebar-nav {
  padding: 12px 8px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
  cursor: pointer;
  color: rgba(255, 255, 255, 0.7);
  transition: all 0.2s;
  margin-bottom: 4px;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}

.nav-item.active {
  background: rgba(64, 158, 255, 0.2);
  color: #409eff;
}

.nav-label {
  font-size: 14px;
}
</style>
