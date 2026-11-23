import { createRouter, createWebHistory } from 'vue-router'

import { authStore } from '@/stores/authStore.js'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'overview',
      component: () => import('@/views/AppShellView.vue'),
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
})

router.beforeEach(async to => {
  await authStore.initialize()
  if (to.name !== 'login' && !authStore.authenticated.value)
    return { name: 'login', query: { redirect: to.fullPath } }
  if (to.name === 'login' && authStore.authenticated.value) return { name: 'overview' }
})

export default router
