<script setup>
import { computed } from 'vue'
import { t } from '@/i18n/index.js'
// A network-health adapter can supply this prop; browser connectivity alone is not proof of health.
const props = defineProps({ status: { type: String, default: null } })
const state = computed(() => ['online', 'offline'].includes(props.status) ? props.status : 'unknown')
const label = computed(() => t(`dashboard.networkStates.${state.value}`))
</script>
<template>
  <section class="connectivity-panel overview-tool-panel" :data-state="state" aria-label="網路">
    <h2>網路</h2>
    <svg class="network-signal" viewBox="0 0 64 48" aria-hidden="true"><path class="signal-arc outer" d="M7 16 Q32 -5 57 16"/><path class="signal-arc middle" d="M15 25 Q32 10 49 25"/><path class="signal-arc inner" d="M24 34 Q32 27 40 34"/><circle cx="32" cy="42" r="2"/></svg>
    <p aria-live="polite">{{ label }}</p>
  </section>
</template>
<style scoped>
.connectivity-panel{display:grid;grid-template-rows:auto minmax(0,1fr) auto;align-items:center;justify-items:center;min-height:0;padding:12px 14px;gap:6px}h2{justify-self:start;margin:0;font-size:13px;font-weight:500}p{margin:0;font-size:11px;color:var(--text-secondary)}.network-signal{width:54px;max-height:100%;color:var(--color-neutral);fill:currentColor}.signal-arc{fill:none;stroke:currentColor;stroke-width:2.5;stroke-linecap:round;animation:signal-flow 2.1s ease-in-out infinite}.middle{animation-delay:.2s}.outer{animation-delay:.4s}[data-state=online] .network-signal{color:var(--theme-primary)}[data-state=offline] .signal-arc{animation:none;opacity:.35}@keyframes signal-flow{0%,100%{opacity:.25}45%,65%{opacity:1}}@media(prefers-reduced-motion:reduce){.signal-arc{animation:none;opacity:1}}
h2{display:flex;align-items:center;gap:7px}h2 svg{flex:none;color:var(--theme-primary)}
</style>
