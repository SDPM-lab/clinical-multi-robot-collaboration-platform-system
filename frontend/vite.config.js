import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'
import tailwindcss from '@tailwindcss/vite'

const uiFontScalePlugin = {
  postcssPlugin: 'ui-font-size-scale',
  Declaration(declaration) {
    if (declaration.prop !== 'font-size' || declaration.value.trim() === '0') return
    if (/^(inherit|initial|unset|revert|revert-layer)$/i.test(declaration.value.trim())) return
    if (declaration.value.includes('--ui-font-scale')) return
    declaration.value = `calc((${declaration.value}) * var(--ui-font-scale, 1))`
  },
}

// https://vite.dev/config/
export default defineConfig({
  root: fileURLToPath(new URL('.', import.meta.url)),
  plugins: [
    vue(),
    vueDevTools(),
    tailwindcss(),
  ],
  css: {
    postcss: {
      plugins: [uiFontScalePlugin],
    },
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: { proxy: { '/api': 'http://localhost:5100' } },
  test: {
    environment: 'jsdom',
    globals: false,
    include: ['test/**/*.test.js'],
  },
})
