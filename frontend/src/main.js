import './styles/theme.css'
import './app.css'

import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { i18n, installGlobalTranslation } from './i18n/index.js'

createApp(App).use(router).use(i18n).mount('#app')
installGlobalTranslation(document.getElementById('app'))
