<script setup>
import { computed, watch } from 'vue'
import { BatteryCharging, ListChecks } from '@lucide/vue'
import { useCountUp } from '@/composables/useCountUp.js'
import GlassPanel from './GlassPanel.vue'

const props = defineProps({
  data: {
    type: Object,
    default: null,
  },
  animationKey: { type: Number, default: 0 },
})

const onlineTarget = computed(() => props.data?.online ?? 0)
const activeTarget = computed(() => props.data?.activeTasks ?? 0)
const chargingTarget = computed(() => props.data?.charging ?? 0)
const { displayed: online, restart: restartOnline } = useCountUp(onlineTarget, { duration: 2200 })
const { displayed: activeTasks, restart: restartActiveTasks } = useCountUp(activeTarget, { duration: 2100 })
const { displayed: charging, restart: restartCharging } = useCountUp(chargingTarget, { duration: 2100 })

watch(() => props.animationKey, () => {
  restartOnline()
  restartActiveTasks()
  restartCharging()
})
</script>

<template>
  <GlassPanel title="車隊概況">
    <template #header-meta><small class="demo-label">展示資料</small></template>
    <div class="fleet-primary">
      <strong>{{ online }} <span>/ {{ data?.total ?? 0 }}</span></strong>
      <small>機器人上線</small>
    </div>
    <div class="online-segments" aria-label="車隊上線比例">
      <span
        v-for="index in (data?.total ?? 0)"
        :key="`${animationKey}-${index}`"
        class="online-segment"
        :class="{ 'online-segment--active': index <= (data?.online ?? 0) }"
        :style="{ '--segment-delay': `${1050 + (index - 1) * 100}ms` }"
      ></span>
    </div>
    <dl class="fleet-secondary">
      <div class="panel-row">
        <dt><ListChecks :size="17" />執行中任務</dt>
        <dd>{{ activeTasks }}</dd>
      </div>
      <div class="panel-row">
        <dt><BatteryCharging :size="17" />充電中</dt>
        <dd>{{ charging }}</dd>
      </div>
    </dl>
  </GlassPanel>
</template>

<style scoped>
.demo-label { color: var(--text-secondary); font-size: 12.5px; font-weight: 500; opacity: 0.78; }
.fleet-primary { display: flex; align-items: baseline; gap: 9px; margin-top: 3px; }
.fleet-primary strong { color: var(--text-primary); font-size: 28px; font-weight: 670; line-height: 1; }
.fleet-primary strong span { color: var(--text-secondary); font-size: 14px; font-weight: 550; }
.fleet-primary small { color: var(--text-secondary); font-size: 12.5px; }
.online-segments { display: flex; gap: 6px; margin: 7px 0 5px; }
.online-segment { flex: 1; height: 7px; background: var(--progress-track); border-radius: 5px; }
.online-segment--active { animation: segment-online 240ms ease-out var(--segment-delay) both; }
.fleet-secondary { margin: 0; }
.panel-row { display: flex; align-items: center; justify-content: space-between; min-height: 36px; gap: 14px; }
.panel-row dt { display: flex; align-items: center; gap: 10px; color: var(--text-secondary); font-size: 14px; }
.panel-row dt :deep(svg) { color: var(--wood-accent); stroke-width: 1.7; }
.panel-row dd { margin: 0; color: var(--text-primary); font-size: 16px; font-weight: 650; }
@keyframes segment-online { from { background: var(--progress-track); transform: scaleX(0.15); } to { background: var(--wood-accent); transform: scaleX(1); } }
@media (prefers-reduced-motion: reduce) { .online-segment--active { animation: none; background: var(--wood-accent); } }
</style>
