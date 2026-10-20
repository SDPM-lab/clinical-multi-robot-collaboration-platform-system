<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps({ tasks: { type: Array, default: () => [] }, robotId: String, active: Boolean })
const finishedStatuses = new Set(['completed', 'failed', 'cancelled', 'error'])
const finishedTasks = computed(() => props.tasks.filter((task) => (
  task.robotId === props.robotId && finishedStatuses.has(task.status)
)))
const successfulCount = computed(() => finishedTasks.value.filter((task) => task.status === 'completed').length)
const anomalyCount = computed(() => finishedTasks.value.length - successfulCount.value)
const accuracy = computed(() => finishedTasks.value.length
  ? successfulCount.value / finishedTasks.value.length * 100
  : null)
const chartPoints = computed(() => {
  if (!finishedTasks.value.length) return []
  let successes = 0
  return finishedTasks.value.map((task, index) => {
    if (task.status === 'completed') successes += 1
    const value = successes / (index + 1) * 100
    return { x: finishedTasks.value.length === 1 ? 110 : 10 + index / (finishedTasks.value.length - 1) * 200, y: 77 - value * .58 }
  })
})
const linePoints = computed(() => chartPoints.value.map((point) => `${point.x},${point.y}`).join(' '))
const areaPoints = computed(() => chartPoints.value.length ? `10,80 ${linePoints.value} 210,80` : '')
const peak = computed(() => chartPoints.value.reduce((best, point) => !best || point.y < best.y ? point : best, null))
const shown = ref(0)
let frame
let entranceTimer

function animateAccuracy() {
  cancelAnimationFrame(frame)
  const target = accuracy.value || 0
  const from = shown.value
  const start = performance.now()
  const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  const duration = reduced ? 0 : 1100
  const animate = (now) => {
    const t = duration === 0 ? 1 : Math.min(1, (now - start) / duration)
    shown.value = from + (target - from) * (1 - (1 - t) ** 3)
    if (t < 1) frame = requestAnimationFrame(animate)
  }
  frame = requestAnimationFrame(animate)
}

watch(() => props.active, (active) => {
  if (!active) return
  clearTimeout(entranceTimer)
  const reduced = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  entranceTimer = window.setTimeout(animateAccuracy, reduced ? 0 : 120)
}, { immediate: true })
watch(accuracy, () => { if (props.active) animateAccuracy() })
onBeforeUnmount(() => {
  cancelAnimationFrame(frame)
  clearTimeout(entranceTimer)
})
</script>

<template>
  <section class="task-accuracy-card" :class="{ 'is-active': active }" aria-label="任務準確率">
    <header><span>TASK ACCURACY</span><small>任務準確率</small></header>
    <template v-if="accuracy !== null">
      <div class="accuracy-summary"><strong>{{ shown.toFixed(1) }}%</strong><span>成功 {{ successfulCount }}<br>異常 {{ anomalyCount }}</span></div>
      <svg class="accuracy-chart" viewBox="0 0 220 84" role="img" :aria-label="`任務準確率 ${accuracy.toFixed(1)}%`">
        <defs><linearGradient id="accuracy-area" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--theme-primary)" stop-opacity=".28"/><stop offset="1" stop-color="var(--theme-primary)" stop-opacity=".01"/></linearGradient></defs>
        <polygon class="accuracy-area" :points="areaPoints"/>
        <polyline class="accuracy-line" pathLength="1" :points="linePoints"/>
        <circle v-if="peak" class="accuracy-peak" :cx="peak.x" :cy="peak.y" r="3"/>
      </svg>
    </template>
    <p v-else class="accuracy-empty">尚無已完成任務</p>
  </section>
</template>
