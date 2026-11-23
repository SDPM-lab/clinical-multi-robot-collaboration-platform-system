<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { apiBaseUrl, sessionFetch } from '@/services/sessionApi.js'
import { t } from '@/i18n/index.js'

const reconnecting = ref(false)
let stopped = false
let retryTimer
let timeoutTimer
let controller

async function checkConnection() {
  controller = new AbortController()
  timeoutTimer = window.setTimeout(() => controller.abort(), 5000)
  try {
    const response = await sessionFetch(`${apiBaseUrl}/api/auth/me`, {
      signal: controller.signal,
      cache: 'no-store',
    })
    if (!stopped) reconnecting.value = !response.ok && response.status !== 401
  } catch {
    if (!stopped) reconnecting.value = true
  } finally {
    window.clearTimeout(timeoutTimer)
    if (!stopped) retryTimer = window.setTimeout(checkConnection, 5000)
  }
}

onMounted(checkConnection)
onBeforeUnmount(() => {
  stopped = true
  window.clearTimeout(retryTimer)
  window.clearTimeout(timeoutTimer)
  controller?.abort()
})
</script>

<template>
  <div v-if="reconnecting" class="backend-reconnect" role="status" aria-live="polite">
    <span class="backend-reconnect__spinner" aria-hidden="true"></span>
    <strong>{{ t('backendConnection.reconnecting') }}</strong>
    <span>{{ t('backendConnection.description') }}</span>
  </div>
</template>

<style scoped>
.backend-reconnect {
  position: fixed;
  inset: 0;
  z-index: 9998;
  display: grid;
  place-content: center;
  justify-items: center;
  gap: 12px;
  padding: 24px;
  color: var(--text-primary);
  background: var(--app-bg, #eceeed);
  background: color-mix(in srgb, var(--app-bg, #eceeed) 92%, transparent);
  text-align: center;
}

.backend-reconnect__spinner {
  width: 28px;
  height: 28px;
  border: 3px solid var(--info-divider, #c9c9c9);
  border-top-color: var(--theme-primary, #b7755f);
  border-radius: 50%;
  animation: backend-reconnect-spin .8s linear infinite;
}

@keyframes backend-reconnect-spin {
  to { transform: rotate(360deg); }
}

@media (prefers-reduced-motion: reduce) {
  .backend-reconnect__spinner { animation-duration: 1.8s; }
}
</style>
