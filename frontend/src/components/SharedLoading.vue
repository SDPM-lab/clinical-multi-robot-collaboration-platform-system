<script setup>
import { t } from '@/i18n/index.js'

defineProps({ loading: Boolean, detail: { type: String, default: '' }, error: { type: String, default: '' }, errorTitle: { type: String, default: '' } })
</script>
<template>
  <Transition name="shared-loading">
    <div v-if="loading" class="scene-message" role="status" aria-live="polite"><span class="scene-spinner" aria-hidden="true"></span><strong>{{ t('common.loading') }}</strong><span>{{ detail || t('common.preparingData') }}</span></div>
    <div v-else-if="error" class="scene-message scene-message--error" role="alert"><strong>{{ errorTitle || t('common.loadFailed') }}</strong><span>{{error}}</span><slot name="error-action"/></div>
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
  background: transparent;
  border: 0;
  box-shadow: none;
  transform: translate(-50%, -50%);
  backdrop-filter: none;
  border-radius: var(--info-radius);
}

.scene-message strong {
  font-size: 13px;
}

.scene-message span:last-child {
  color: var(--text-secondary);
  font-size: 0.8rem;
  line-height: 1.5;
  text-align: center;
}

.scene-message--error {
  background: var(--info-background);
  border: var(--info-border);
  box-shadow: var(--info-shadow);
}

.scene-message--error strong {
  color: var(--semantic-error);
}

.scene-spinner {
  width: 24px;
  height: 24px;
  border: 2px solid var(--info-divider);
  border-top-color: var(--theme-primary);
  border-right-color: var(--color-secondary);
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
