import { createRouter, createWebHistory } from 'vue-router'

import AppShellView from '@/views/AppShellView.vue'
import LoginView from '@/views/LoginView.vue'
import { authStore } from '@/stores/authStore.js'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'overview',
      component: AppShellView,
    },
    {
      path: '/login',
      name: 'login',
      component: LoginView,
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
