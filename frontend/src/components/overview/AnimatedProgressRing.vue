<script setup>
import { computed, watch } from 'vue'
import { useCountUp } from '@/composables/useCountUp.js'

const props = defineProps({
  value: { type: Number, required: true },
  animationKey: { type: Number, default: 0 },
  label: { type: String, default: '今日完成率' },
})

const radius = 49
const circumference = 2 * Math.PI * radius
const target = computed(() => Math.min(Math.max(props.value, 0), 100))
const { displayed, restart } = useCountUp(target, { duration: 2200 })
const dashOffset = computed(() => circumference * (1 - displayed.value / 100))

watch(() => props.animationKey, restart)
</script>

<template>
  <div class="progress-ring" :aria-label="`${label} ${displayed}%`">
    <svg viewBox="0 0 110 110" aria-hidden="true">
      <circle class="progress-ring__track" cx="55" cy="55" :r="radius" />
      <circle
        class="progress-ring__value"
        cx="55"
        cy="55"
        :r="radius"
        :stroke-dasharray="circumference"
        :stroke-dashoffset="dashOffset"
      />
    </svg>
    <strong>{{ displayed }}%</strong>
    <span>{{ label }}</span>
  </div>
</template>

<style scoped>
.progress-ring {
  position: relative;
  width: 86px;
  height: 84px;
}

.progress-ring svg {
  position: absolute;
  top: 0;
  left: 8px;
  width: 70px;
  height: 70px;
  overflow: visible;
  transform: rotate(-90deg);
}

.progress-ring circle {
  fill: none;
  stroke-width: 8;
}

.progress-ring__track {
  stroke: var(--progress-track);
}

.progress-ring__value {
  stroke: var(--accent-orange);
  stroke-linecap: round;
}

.progress-ring strong {
  position: absolute;
  top: 22px;
  left: 0;
  width: 100%;
  color: var(--text-primary);
  font-size: 22px;
  line-height: 1;
  text-align: center;
}

.progress-ring span {
  position: absolute;
  top: 73px;
  left: 0;
  width: 100%;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1;
  text-align: center;
}
</style>
