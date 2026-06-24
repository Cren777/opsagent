import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      name: 'chat',
      component: () => import('@/views/ChatView.vue'),
    },
    {
      path: '/datasources',
      name: 'datasources',
      component: () => import('@/views/DataSourceView.vue'),
    },
    {
      path: '/knowledge',
      name: 'knowledge',
      component: () => import('@/views/KnowledgeView.vue'),
    },
    {
      path: '/logs-cases',
      name: 'logs-cases',
      component: () => import('@/views/LogsCasesView.vue'),
    },
    {
      path: '/diagnostics',
      name: 'diagnostics',
      component: () => import('@/views/DiagnosticsView.vue'),
    },
    {
      path: '/indexes',
      name: 'indexes',
      component: () => import('@/views/IndexManagementView.vue'),
    },
    {
      path: '/llm',
      name: 'llm',
      component: () => import('@/views/LLMConfigView.vue'),
    },
  ],
})

router.beforeEach(async (to) => {
  const authStore = useAuthStore()
  if (!authStore.initialized) {
    await authStore.bootstrap()
  }

  if (authStore.token && !authStore.user) {
    await authStore.fetchMe()
  }

  if (to.meta.public) {
    return authStore.isAuthenticated && to.path === '/login' ? '/' : true
  }

  if (!authStore.isAuthenticated) {
    return '/login'
  }

  return true
})

export default router
