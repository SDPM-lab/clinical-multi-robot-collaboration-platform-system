<script setup>
import { computed, onMounted, useId, watch } from 'vue'
import { useCountUp } from '@/composables/useCountUp.js'

const props = defineProps({
  value: { type: Number, default: 0 },
  label: { type: String, default: '' },
  compact: { type: Boolean, default: false },
  color: { type: String, default: '#e88932' },
})
const safeValue = computed(() => Math.min(100, Math.max(0, props.value)))
const counter = useCountUp(safeValue, { duration: 2500 })
const progressLength = computed(() => counter.displayed.value * (2 / 3))
const gradientId = `completion-${useId().replace(/:/g, '')}`
onMounted(counter.restart)
watch(() => props.value, counter.restart)
</script>

<template>
  <div class="completion-gauge" :class="{ 'is-compact': compact }" role="img" :aria-label="`${label || '完成率'} ${safeValue}%`">
    <span v-if="label" class="gauge-label">{{ label }}</span>
    <div class="gauge-visual">
      <svg viewBox="0 0 160 112" aria-hidden="true">
        <defs><linearGradient :id="gradientId" x1="0" y1="1" x2="1" y2="0"><stop offset="0" :stop-color="color" stop-opacity=".82" /><stop offset="1" stop-color="#ffd36d" /></linearGradient></defs>
        <circle class="gauge-track" cx="80" cy="68" r="54" pathLength="100" />
        <circle class="gauge-value" cx="80" cy="68" r="54" pathLength="100" :style="{ stroke: `url(#${gradientId})`, strokeDasharray: `${progressLength} 100` }" />
      </svg>
      <strong>{{ counter.displayed }}%</strong>
    </div>
  </div>
</template>

<style scoped>
.completion-gauge{display:grid;width:188px;justify-items:center}.gauge-label{margin-bottom:-4px;color:var(--overview-muted);font-size:12px;font-weight:650}.gauge-visual{position:relative;width:188px;height:112px}.gauge-visual svg{display:block;width:100%;height:100%}.gauge-track,.gauge-value{fill:none;stroke-width:11;stroke-linecap:round;stroke-dasharray:66.67 100;transform:rotate(150deg);transform-origin:80px 68px}.gauge-track{stroke:rgba(83,90,86,.12)}.gauge-value{transition:stroke-dasharray 70ms linear}.gauge-visual strong{position:absolute;top:47px;right:0;left:0;text-align:center;font-size:29px;line-height:1;font-weight:720;letter-spacing:-.04em}.completion-gauge.is-compact{width:92px}.is-compact .gauge-label{margin-bottom:-10px;font-size:10px}.is-compact .gauge-visual{width:92px;height:76px}.is-compact .gauge-visual strong{top:36px;font-size:18px}.is-compact .gauge-track,.is-compact .gauge-value{stroke-width:9px}:global([data-theme=dark]) .gauge-track{stroke:rgba(255,255,255,.11)}
@media(prefers-reduced-motion:reduce){.gauge-value{transition:none}}
</style>
