<script setup>
import { computed } from 'vue'
import { t } from '@/i18n/index.js'
const props = defineProps({ status: { type: String, default: null } })
const states = { connected: 'online', connecting: 'connecting', disconnected: 'offline' }
const state = computed(() => states[props.status] || 'unknown')
const label = computed(() => t(`rosConnection.${states[props.status] ? props.status : 'unknown'}`))
</script>
<template>
  <section class="connectivity-panel overview-tool-panel" :data-state="state" :aria-label="t('dashboard.network')">
    <h2>{{ t('dashboard.network') }}</h2>
    <svg class="network-signal" viewBox="0 0 64 48" aria-hidden="true"><path class="signal-arc outer" d="M7 16 Q32 -5 57 16"/><path class="signal-arc middle" d="M15 25 Q32 10 49 25"/><path class="signal-arc inner" d="M24 34 Q32 27 40 34"/><circle cx="32" cy="42" r="2"/></svg>
    <p aria-live="polite">{{ label }}</p>
  </section>
</template>
<style scoped>
.connectivity-panel{display:grid;grid-template-rows:auto minmax(0,1fr) auto;align-items:center;justify-items:center;min-height:0;padding:12px 14px;gap:6px}h2{justify-self:start;margin:0;font-size:13px;font-weight:500}p{margin:0;font-size:11px;color:var(--text-secondary)}.network-signal{width:54px;max-height:100%;color:var(--color-neutral);fill:currentColor}.signal-arc{fill:none;stroke:currentColor;stroke-width:2.5;stroke-linecap:round;animation:signal-flow 2.1s ease-in-out infinite}.middle{animation-delay:.2s}.outer{animation-delay:.4s}[data-state=online] .network-signal{color:var(--theme-primary)}[data-state=connecting] .network-signal{color:var(--semantic-warning)}[data-state=offline] .signal-arc,[data-state=unknown] .signal-arc{animation:none;opacity:.35}@keyframes signal-flow{0%,100%{opacity:.25}45%,65%{opacity:1}}@media(prefers-reduced-motion:reduce){.signal-arc{animation:none;opacity:1}}
h2{display:flex;align-items:center;gap:7px}h2 svg{flex:none;color:var(--theme-primary)}
</style>
