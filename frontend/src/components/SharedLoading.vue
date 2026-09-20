<script setup>
defineProps({ loading: Boolean, detail: { type: String, default: '準備資料中…' }, error: { type: String, default: '' }, errorTitle: { type: String, default: '載入失敗' } })
</script>
<template>
  <Transition name="shared-loading">
    <div v-if="loading" class="scene-message" role="status" aria-live="polite"><span class="scene-spinner" aria-hidden="true"></span><strong>Loading...</strong><span>{{detail}}</span></div>
    <div v-else-if="error" class="scene-message scene-message--error" role="alert"><strong>{{errorTitle}}</strong><span>{{error}}</span><slot name="error-action"/></div>
  </Transition>
</template>
<style scoped>
.scene-message {
  font-size: 11px;
  position: absolute;
  z-index: 2;
  top: 50%;
  left: 50%;
  display: grid;
  min-width: 220px;
  max-width: min(420px, calc(100% - 40px));
  justify-items: center;
  gap: 10px;
  padding: 22px 26px;
  color: var(--text-primary);
  background: var(--message-background);
  border: 1px solid var(--message-border);
  box-shadow: var(--glass-shadow);
  transform: translate(-50%, -50%);
  backdrop-filter: blur(10px);
}

.scene-message span:last-child {
  color: var(--text-secondary);
  font-size: 0.875rem;
  line-height: 1.5;
  text-align: center;
}

.scene-message--error {
  border-color: rgba(170, 82, 54, 0.2);
}

.scene-message--error strong {
  color: #9d4e36;
}

.scene-spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--theme-primary-soft);
  border-top-color: var(--theme-primary);
  border-right-color: #d5ad4e;
  border-radius: 50%;
  animation: scene-spin 0.8s linear infinite;
}


@keyframes scene-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .scene-spinner {
    animation-duration: 1.8s;
  }
}

.shared-loading-enter-active,.shared-loading-leave-active{transition:opacity 200ms ease}.shared-loading-enter-from,.shared-loading-leave-to{opacity:0}
</style>
