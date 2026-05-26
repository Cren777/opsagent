import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
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

export default router
