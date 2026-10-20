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
