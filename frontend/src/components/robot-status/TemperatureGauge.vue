<script setup>
import { computed, onBeforeUnmount, watch } from 'vue'
import { TriangleAlert } from '@lucide/vue'
import { useCountUp } from '@/composables/useCountUp.js'
import { thermalState } from '@/config/robotHmi.js'

const props = defineProps({ value: { type: Number, default: null }, active: Boolean })
const { displayed, restart } = useCountUp(() => props.value, { duration: 2200 })
const state = computed(() => thermalState(props.value))
const progress = computed(() => Math.max(0, Math.min(1, displayed.value / 100)))
const endpoint = computed(() => {
  const angle = (150 + progress.value * 240) * Math.PI / 180
  return { x: 100 + Math.cos(angle) * 72, y: 100 + Math.sin(angle) * 72 }
})
let entranceTimer

watch(() => props.active, (active) => {
  if (!active) return
  clearTimeout(entranceTimer)
  const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  entranceTimer = window.setTimeout(restart, reduced ? 0 : 3300)
}, { immediate: true })
onBeforeUnmount(() => clearTimeout(entranceTimer))
</script>

<template>
  <section class="hmi-gauge thermal" :class="`is-${state}`" aria-label="溫度儀表">
    <div class="gauge-heading"><span>THERMAL</span><small>MOTOR TEMPERATURE</small></div>
    <div class="thermal-arc">
      <svg viewBox="0 0 200 178" aria-hidden="true">
        <defs><linearGradient id="thermal-gradient" x1="0" y1="1" x2="1" y2="0"><stop offset="0" stop-color="#72A89C"/><stop offset=".5" stop-color="#A8B87A"/><stop offset=".72" stop-color="#D1A45F"/><stop offset="1" stop-color="#B9635D"/></linearGradient></defs>
        <circle class="thermal-arc-track" cx="100" cy="100" r="72" pathLength="100"/>
        <circle class="thermal-arc-value" cx="100" cy="100" r="72" pathLength="100" :stroke-dasharray="`${progress * 66.67} 100`"/>
        <circle v-if="value !== null" class="thermal-endpoint" :cx="endpoint.x" :cy="endpoint.y" r="3.5"/>
      </svg>
      <div class="thermal-reading"><strong>{{ value == null ? '待接入' : displayed }}<em v-if="value !== null">°C</em></strong><span>{{ state.toUpperCase() }}</span></div>
    </div>
    <p v-if="state === 'critical'" role="alert"><TriangleAlert :size="15"/>馬達溫度過高</p>
    <p v-else>{{ state === 'warning' ? '溫度偏高，請留意' : state === 'unknown' ? '尚無溫度資料' : '溫度在正常範圍' }}</p>
  </section>
</template>
