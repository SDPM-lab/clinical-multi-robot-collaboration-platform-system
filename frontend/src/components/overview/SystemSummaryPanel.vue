<script setup>
import { computed, watch } from 'vue'
import { Database, OctagonAlert, TriangleAlert } from '@lucide/vue'
import { useCountUp } from '@/composables/useCountUp.js'
import GlassPanel from './GlassPanel.vue'

const props = defineProps({
  data: {
    type: Object,
    default: null,
  },
  animationKey: { type: Number, default: 0 },
})

const criticalTarget = computed(() => props.data?.critical ?? 0)
const warningTarget = computed(() => props.data?.warning ?? 0)
const { displayed: critical, restart: restartCritical } = useCountUp(criticalTarget, { duration: 2100 })
const { displayed: warning, restart: restartWarning } = useCountUp(warningTarget, { duration: 2200 })

watch(() => props.animationKey, () => {
  restartCritical()
  restartWarning()
})
</script>

<template>
  <GlassPanel title="系統摘要">
    <template #header-meta><small class="demo-label">展示資料</small></template>
    <div class="system-connection">
      <span class="connection-dot" :class="{ 'connection-dot--online': data?.connected }"></span>
      <span>系統連線</span>
      <strong>{{ data?.connected ? '正常' : '等待連線' }}</strong>
    </div>
    <div class="alert-metrics">
      <div><OctagonAlert :size="17" /><span>嚴重警報</span><strong>{{ critical }}</strong></div>
      <div><TriangleAlert :size="17" /><span>一般警告</span><strong>{{ warning }}</strong></div>
    </div>
    <div class="data-source"><Database :size="16" />資料來源 <strong>{{ data?.source ?? '—' }}</strong></div>
  </GlassPanel>
</template>

<style scoped>
.demo-label { color: var(--text-secondary); font-size: 12.5px; font-weight: 500; opacity: 0.78; }
.system-connection { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; align-items: center; min-height: 36px; gap: 9px; color: var(--text-secondary); font-size: 14px; }
.system-connection strong { color: var(--text-primary); font-size: 16px; }
.connection-dot { width: 9px; height: 9px; background: rgba(120, 124, 121, 0.28); border-radius: 50%; }
.connection-dot--online { background: var(--wood-accent); }
.alert-metrics { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-top: 4px; }
.alert-metrics > div { display: grid; grid-template-columns: auto minmax(0, 1fr); align-items: center; min-width: 0; min-height: 48px; gap: 3px 8px; color: var(--text-secondary); }
.alert-metrics svg { grid-row: 1 / 3; color: var(--wood-accent); }
.alert-metrics span { font-size: 12.5px; }
.alert-metrics strong { color: var(--text-primary); font-size: 18px; line-height: 1; }
.data-source { display: grid; grid-template-columns: auto auto minmax(0, 1fr); align-items: center; min-height: 36px; gap: 7px; color: var(--text-secondary); font-size: 12.5px; }
.data-source strong { min-width: 0; color: var(--text-primary); font-weight: 550; overflow-wrap: anywhere; text-align: right; }
</style>
