<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import SessionList from '@/components/chat/SessionList.vue'
import ChangePasswordDialog from '@/components/auth/ChangePasswordDialog.vue'
import UserProfileDialog from '@/components/auth/UserProfileDialog.vue'
import { useAuthStore } from '@/stores/auth'

defineProps<{ collapsed: boolean }>()
defineEmits<{ toggle: [] }>()

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const profileDialogVisible = ref(false)
const passwordDialogVisible = ref(false)
const avatarLetter = computed(() => (authStore.user?.username || 'U').slice(0, 1).toUpperCase())

const navItems = [
  { path: '/', icon: 'ChatDotRound', label: '鏅鸿兘瀵硅瘽' },
  { path: '/knowledge', icon: 'Collection', label: '鐭ヨ瘑搴撶鐞?' },
  { path: '/logs-cases', icon: 'Document', label: '鏃ュ織涓庢渚?' },
  { path: '/diagnostics', icon: 'Tools', label: '璇婃柇宸ュ叿' },
  { path: '/indexes', icon: 'Operation', label: '绱㈠紩绠＄悊' },
  { path: '/datasources', icon: 'Coin', label: '鏁版嵁婧愰厤缃?' },
  { path: '/llm', icon: 'Cpu', label: '澶фā鍨嬮厤缃?' },
]

function navigateTo(path: string) {
  router.push(path)
}

function logout() {
  authStore.logout()
  router.push('/login')
}
</script>

<template>
  <aside class="app-sidebar" :class="{ collapsed }">
    <div class="sidebar-header">
      <div class="logo">
        <el-icon :size="24"><Monitor /></el-icon>
        <span v-show="!collapsed" class="logo-text">OpsAgent</span>
      </div>
      <el-tag v-show="!collapsed" size="small" type="info">杩愮淮瀹㈡湇</el-tag>
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

    <div class="sidebar-user">
      <el-dropdown trigger="click">
        <button class="user-button" type="button">
          <span class="avatar">{{ avatarLetter }}</span>
          <span v-show="!collapsed" class="user-meta">
            <span class="username">{{ authStore.user?.username }}</span>
            <span class="role">{{ authStore.user?.role }}</span>
          </span>
          <el-icon v-show="!collapsed"><ArrowDown /></el-icon>
        </button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item @click="profileDialogVisible = true">修改用户名</el-dropdown-item>
            <el-dropdown-item @click="passwordDialogVisible = true">修改密码</el-dropdown-item>
            <el-dropdown-item divided @click="logout">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>

    <UserProfileDialog v-model="profileDialogVisible" />
    <ChangePasswordDialog v-model="passwordDialogVisible" />
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

.sidebar-user {
  margin-top: auto;
  padding: 12px 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.user-button {
  width: 100%;
  min-height: 48px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px;
  border: 0;
  border-radius: 8px;
  color: #fff;
  background: rgba(255, 255, 255, 0.06);
  cursor: pointer;
}

.user-button:hover {
  background: rgba(255, 255, 255, 0.1);
}

.avatar {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
  border-radius: 50%;
  background: var(--ops-primary);
  color: #fff;
  font-weight: 800;
}

.user-meta {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
}

.username,
.role {
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.username {
  font-size: 13px;
  font-weight: 700;
}

.role {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.58);
}

.app-sidebar.collapsed .sidebar-user {
  padding: 12px 8px;
}

.app-sidebar.collapsed .user-button {
  justify-content: center;
}
</style>
