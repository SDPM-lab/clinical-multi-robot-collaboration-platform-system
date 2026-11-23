import './styles/theme.css'
import './app.css'

import { createApp } from 'vue'
import { installVisualTokens } from './config/visualTokens.js'
import App from './App.vue'
import router from './router'
import { i18n, installGlobalTranslation } from './i18n/index.js'

installVisualTokens(document.documentElement)

createApp(App).use(router).use(i18n).mount('#app')
installGlobalTranslation(document.getElementById('app'))

router.isReady().then(() => {
  document.getElementById('startup-loading')?.remove()
}).catch(error => {
  console.error('Failed to initialize the application router:', error)
  const loading = document.getElementById('startup-loading')
  if (loading) {
    loading.setAttribute('role', 'alert')
    loading.textContent = i18n.global.locale.value === 'en'
      ? 'Unable to load the page. Please refresh and try again.'
      : '無法載入頁面，請重新整理後再試。'
  }
})
