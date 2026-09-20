<script setup>
import { computed, onBeforeUnmount, ref, useId, watch } from 'vue'
import { batteryLiquidColors } from '@/config/robotHmi.js'

const props = defineProps({ value: Number, charging: Boolean, runtime: String, active: Boolean })
const shown = ref(0)
const uid = useId().replace(/[^a-zA-Z0-9_-]/g, '')
const clipId = `battery-clip-${uid}`
const gradientId = `battery-gradient-${uid}`
const colors = computed(() => batteryLiquidColors(props.value, props.charging))
const liquidHeight = computed(() => Math.max(0, Math.min(68, shown.value * .68)))
const liquidY = computed(() => 86 - liquidHeight.value)
let frame
let entranceTimer

function animateTo(value, duration = 900) {
  cancelAnimationFrame(frame)
  const from = shown.value
  const start = performance.now()
  const animate = (now) => {
    const t = duration === 0 ? 1 : Math.min(1, (now - start) / duration)
    shown.value = from + (value - from) * (1 - (1 - t) ** 3)
    if (t < 1) frame = requestAnimationFrame(animate)
  }
  frame = requestAnimationFrame(animate)
}

watch(() => props.active, (active) => {
  if (!active) return
  clearTimeout(entranceTimer)
  const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  entranceTimer = window.setTimeout(
    () => animateTo(props.value || 0, reduced ? 0 : 1200),
    reduced ? 0 : 3200,
  )
}, { immediate: true })
watch(() => props.value, (value, previous) => {
  if (props.active && previous !== undefined) animateTo(value || 0)
})
onBeforeUnmount(() => {
  cancelAnimationFrame(frame)
  clearTimeout(entranceTimer)
})
</script>

<template>
  <section
    class="hmi-gauge energy"
    :class="{ 'is-charging': charging, 'is-warning': !charging && value > 20 && value <= 40, 'is-critical': !charging && value <= 20 }"
    aria-label="液體電池儀表"
  >
    <div class="gauge-heading"><span>BATTERY</span><small>{{ charging ? 'CHARGING' : 'ENERGY LEVEL' }}</small></div>
    <div class="liquid-battery-wrap">
      <svg class="liquid-battery" viewBox="0 0 260 104" role="img" :aria-label="`電量 ${Math.round(shown)}%`">
        <defs>
          <clipPath :id="clipId"><rect x="15" y="18" width="218" height="68" rx="22"/></clipPath>
          <linearGradient :id="gradientId" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" :stop-color="colors[0]"/><stop offset="1" :stop-color="colors[1]"/>
          </linearGradient>
        </defs>
        <rect class="battery-shell" x="8" y="11" width="232" height="82" rx="29"/>
        <path class="battery-terminal" d="M241 37h9c4 0 7 4 7 9v12c0 5-3 9-7 9h-9z"/>
        <g :clip-path="`url(#${clipId})`">
          <rect class="battery-liquid" x="15" :y="liquidY" width="218" :height="liquidHeight + 4" :fill="`url(#${gradientId})`"/>
          <path class="battery-wave battery-wave-back" :d="`M-220 ${liquidY + 2} Q-190 ${liquidY - 2} -160 ${liquidY + 2} T-100 ${liquidY + 2} T-40 ${liquidY + 2} T20 ${liquidY + 2} T80 ${liquidY + 2} T140 ${liquidY + 2} T200 ${liquidY + 2} T260 ${liquidY + 2} T320 ${liquidY + 2} T380 ${liquidY + 2} V104 H-220Z`" :fill="colors[0]"/>
          <path class="battery-wave battery-wave-front" :d="`M-220 ${liquidY} Q-185 ${liquidY + 3} -150 ${liquidY} T-80 ${liquidY} T-10 ${liquidY} T60 ${liquidY} T130 ${liquidY} T200 ${liquidY} T270 ${liquidY} T340 ${liquidY} V104 H-220Z`" :fill="colors[1]"/>
          <g v-if="charging" class="battery-energy-particles"><circle cx="55" cy="78" r="2"/><circle cx="125" cy="82" r="1.7"/><circle cx="190" cy="76" r="2.2"/></g>
        </g>
      </svg>
      <strong class="battery-percentage">{{ Math.round(shown) }}<em>%</em></strong>
    </div>
    <p>{{ runtime ? `預估可運行 ${runtime}` : charging ? '電池正在充電' : '預估可運行時間尚未提供' }}</p>
  </section>
</template>
