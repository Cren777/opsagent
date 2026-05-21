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
      path: '/llm',
      name: 'llm',
      component: () => import('@/views/LLMConfigView.vue'),
    },
  ],
})

export default router
