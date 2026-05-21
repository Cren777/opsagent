<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'
import { useChatStore } from '@/stores/chat'

defineProps<{ collapsed: boolean }>()
defineEmits<{ toggle: [] }>()

const router = useRouter()
const route = useRoute()
const chatStore = useChatStore()

const navItems = [
  { path: '/', icon: 'ChatDotRound', label: '智能对话' },
  { path: '/datasources', icon: 'Coin', label: '数据源配置' },
  { path: '/llm', icon: 'Cpu', label: '大模型配置' },
]

const demoQueries = [
  '如何查看磁盘使用率？',
  '最近一周有哪些critical告警？',
  'web-01服务器CPU使用率100%，帮我排查',
  '数据库连接数满了怎么处理？',
  '每个服务器上运行了多少个服务？',
  '系统日志中出现大量Permission denied错误',
  '过去7天工单平均处理时间是多少？',
  'nginx服务无法启动怎么排查？',
]

function navigateTo(path: string) {
  router.push(path)
}

function sendDemo(query: string) {
  router.push('/')
  setTimeout(() => {
    chatStore.sendStreamMessage(query)
  }, 100)
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

    <div v-show="!collapsed" class="sidebar-demos">
      <div class="demos-header">
        <el-icon :size="14"><Star /></el-icon>
        <span>演示场景</span>
      </div>
      <div class="demos-list">
        <div
          v-for="demo in demoQueries"
          :key="demo"
          class="demo-item"
          @click="sendDemo(demo)"
        >
          {{ demo }}
        </div>
      </div>
    </div>
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

.sidebar-demos {
  flex: 1;
  padding: 0 12px 16px;
  overflow-y: auto;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.demos-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 16px 4px 10px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.5);
}

.demos-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.demo-item {
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.6);
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.demo-item:hover {
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.9);
}
</style>
