<script setup>
import { computed, onMounted, useId } from 'vue'
import { useCountUp } from '@/composables/useCountUp.js'

const props = defineProps({ value: { type: Number, default: 0 }, label: { type: String, default: '全棟完成率' } })
const progress = computed(() => Number.isFinite(props.value) ? Math.max(0, Math.min(100, props.value)) : 0)
const easeInOutCubic = value => value < 0.5 ? 4 * value ** 3 : 1 - ((-2 * value + 2) ** 3) / 2
const { displayed, restart } = useCountUp(progress, { duration: 2800, delay: 180, easing: easeInOutCubic })
const needleAngle = computed(() => -90 + displayed.value * 1.8)
const gradientId = `completion-speed-${useId().replace(/:/g, '')}`
onMounted(restart)
</script>

<template>
  <div class="f1-speed-gauge" role="img" :aria-label="`${label} ${progress}%`">
    <svg viewBox="0 0 240 142" aria-hidden="true">
      <defs>
        <linearGradient :id="gradientId" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stop-color="var(--overview-accent)" />
          <stop offset=".58" stop-color="var(--overview-accent)" />
          <stop offset="1" stop-color="var(--overview-yellow)" />
        </linearGradient>

      </defs>
<path class="speed-bezel" d="M 18 108 A 102 102 0 0 1 222 108" />
      <path class="speed-track" d="M 27 108 A 93 93 0 0 1 213 108" pathLength="100" />
      <path class="speed-arc" d="M 27 108 A 93 93 0 0 1 213 108" pathLength="100" :stroke="`url(#${gradientId})`" :stroke-dasharray="`${displayed} 100`" />
      <g class="speed-ticks"><line v-for="index in 37" :key="index" :style="{ animationDelay: `${150 + Math.abs(index - 19) * 14}ms` }" x1="120" y1="16" x2="120" :y2="index % 6 === 1 ? 27 : 22" :transform="`rotate(${-90 + (index - 1) * 5} 120 108)`" /></g>
      <g class="speed-needle" :transform="`rotate(${needleAngle} 120 108)`"><path d="M 117.5 108 L 120 35 L 122.5 108 Z" /></g>
      <circle class="speed-hub speed-core" cx="120" cy="108" r="5" />
      <text class="speed-number" x="120" y="87" text-anchor="middle">{{ displayed }}</text>
      <text class="speed-unit" x="120" y="101" text-anchor="middle">%</text>
      <text class="speed-limit" x="25" y="127" text-anchor="middle">0</text>
      <text class="speed-limit" x="215" y="127" text-anchor="middle">100</text>
    </svg>
  </div>
</template>

<style scoped>
.f1-speed-gauge{width:100%;max-width:254px;height:164px}.f1-speed-gauge svg{display:block;width:100%;height:100%;overflow:visible}.speed-bezel,.speed-track,.speed-arc{fill:none;stroke-linecap:round}.speed-bezel{stroke:rgba(102,113,125,.12);stroke-width:2}.speed-track{stroke:rgba(122,135,148,.16);stroke-width:9}.speed-arc{stroke-width:9;transition:stroke-dasharray 180ms linear}.speed-ticks{stroke:rgba(102,113,125,.42);stroke-width:1.5}.speed-ticks line:nth-child(6n + 1){stroke:rgba(23,33,43,.72);stroke-width:2.5}.speed-needle{fill:var(--overview-accent-text);transition:transform 200ms linear}.speed-hub{fill:var(--overview-accent-text);stroke:var(--overview-accent-soft);stroke-width:1.5}.speed-limit{fill:var(--text-secondary);font-size:10px}.speed-number{fill:var(--overview-ink);font-size:35px;font-weight:400;font-variant-numeric:tabular-nums;letter-spacing:.025em}.speed-unit{fill:var(--overview-accent-text);font-size:11px;font-weight:400}.speed-track,.speed-bezel{animation:dashboard-fade 2.6s ease-out both}.speed-ticks line{animation:dashboard-fade 1.8s ease-out both}
</style>
