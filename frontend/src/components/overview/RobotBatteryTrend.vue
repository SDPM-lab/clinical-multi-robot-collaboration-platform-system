<script setup>
import { overviewPalette } from '@/styles/overviewTheme.js'
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, useId } from 'vue'
import { batteryPointTime, formatBatteryTimestamp } from '@/data/robotBatteryTrend.js'

const props = defineProps({
  points: { type: Array, default: () => [] },
  robotName: String,
  range: { type: String, default: 'Day' },
  color: { type: String, default: overviewPalette.accent },
  large: Boolean,
})

const root = ref(null)
const hovered = ref(null)
const size = shallowRef({ width: 360, height: 190 })
const id = `battery-trend-${useId().replace(/:/g, '')}`
let observer

onMounted(() => {
  if (typeof ResizeObserver === 'undefined') return
  observer = new ResizeObserver(([entry]) => {
    if (entry.contentRect.width > 0 && entry.contentRect.height > 0) {
      size.value = { width: entry.contentRect.width, height: entry.contentRect.height }
    }
  })
  observer.observe(root.value)
})
onBeforeUnmount(() => observer?.disconnect())

const plot = computed(() => ({
  left: props.large ? 43 : 32,
  right: Math.max(80, size.value.width - (props.large ? 28 : 18)),
  top: props.large ? 28 : 17,
  bottom: Math.max(72, size.value.height - (props.large ? 42 : 29)),
}))
const coordinates = computed(() => {
  const points = props.points
  const first = points[0]?.timestamp
  const last = points.at(-1)?.timestamp
  const timed = points.length > 1 && points.every((point) => Number.isFinite(point.timestamp)) && last > first
  return points.map((point, index) => ({
    ...point,
    x: plot.value.left + (points.length === 1 ? 1 : timed ? (point.timestamp - first) / (last - first) : index / (points.length - 1)) * (plot.value.right - plot.value.left),
    y: plot.value.bottom - point.value / 100 * (plot.value.bottom - plot.value.top),
  }))
})
const path = computed(() => coordinates.value.reduce((value, point, index, points) => {
  if (!index) return `M${point.x},${point.y}`
  const previous = points[index - 1]
  const middle = (previous.x + point.x) / 2
  return `${value} C${middle},${previous.y} ${middle},${point.y} ${point.x},${point.y}`
}, ''))
const activeIndex = computed(() => hovered.value ?? coordinates.value.length - 1)
const active = computed(() => coordinates.value[activeIndex.value])
const tooltipTimestamp = computed(() => formatBatteryTimestamp(active.value))
const tooltipDate = computed(() => tooltipTimestamp.value.includes(' ') ? tooltipTimestamp.value.split(' ')[0] : tooltipTimestamp.value)
const tooltipTime = computed(() => tooltipTimestamp.value.includes(' ') ? tooltipTimestamp.value.split(' ')[1] : '')
const ticks = computed(() => {
  const points = coordinates.value
  const count = Math.min(props.large ? 7 : 4, points.length)
  if (!count) return []
  return [...new Set(Array.from({ length: count }, (_, index) => Math.round(index * (points.length - 1) / Math.max(1, count - 1))))].map((index) => points[index])
})
const tooltipStyle = computed(() => {
  const width = props.large ? 232 : 196
  const x = active.value?.x || 0
  const y = active.value?.y || 0
  return {
    left: `${Math.max(5, Math.min(size.value.width - width - 5, x > size.value.width - width - 28 ? x - width - 12 : x + 12))}px`,
    top: `${Math.max(5, Math.min(size.value.height - 68, y - 57))}px`,
  }
})

function move(event) {
  const bounds = root.value.getBoundingClientRect()
  const x = (event.clientX - bounds.left) * size.value.width / bounds.width
  let nearest = null
  let distance = Infinity
  coordinates.value.forEach((point, index) => {
    if (Math.abs(point.x - x) < distance) {
      nearest = index
      distance = Math.abs(point.x - x)
    }
  })
  hovered.value = nearest
}
function keyboard(event) {
  if (!['ArrowLeft', 'ArrowRight'].includes(event.key) || !coordinates.value.length) return
  event.preventDefault()
  hovered.value = Math.max(0, Math.min(coordinates.value.length - 1, activeIndex.value + (event.key === 'ArrowLeft' ? -1 : 1)))
}
</script>

<template>
  <div ref="root" class="robot-battery-trend" :class="{ 'is-large': large }" :style="{ color, '--trend-color': color }" @pointermove="move" @pointerleave="hovered = null">
    <svg :viewBox="`0 0 ${size.width} ${size.height}`" role="img" :aria-label="`${robotName} ${range} 電量歷史；左右方向鍵選擇時間`" tabindex="0" @keydown="keyboard" @blur="hovered = null">
      <defs>
        <linearGradient :id="`${id}-line`" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" :stop-color="color" stop-opacity=".72"/>
          <stop offset=".52" :stop-color="color"/>
          <stop offset="1" :stop-color="color" stop-opacity=".8"/>
        </linearGradient>
        <linearGradient :id="`${id}-area`" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" :stop-color="color" stop-opacity=".16"/>
          <stop offset="1" :stop-color="color" stop-opacity=".01"/>
        </linearGradient>
      </defs>
      <g v-if="coordinates.length">
        <g class="chart-grid">
          <line v-for="value in [0, 50, 100]" :key="value" :x1="plot.left" :x2="plot.right" :y1="plot.bottom - value / 100 * (plot.bottom - plot.top)" :y2="plot.bottom - value / 100 * (plot.bottom - plot.top)"/>
          <line v-for="tick in ticks" :key="`x-${tick.x}`" :x1="tick.x" :x2="tick.x" :y1="plot.top" :y2="plot.bottom"/>
        </g>
        <g class="y-labels">
          <text :x="plot.left - 7" :y="plot.top + 3" text-anchor="end">100</text>
          <text :x="plot.left - 7" :y="(plot.top + plot.bottom) / 2 + 3" text-anchor="end">50</text>
          <text :x="plot.left - 7" :y="plot.bottom + 3" text-anchor="end">0%</text>
        </g>
        <path v-if="coordinates.length > 1" class="trend-area" :d="`${path} L${coordinates.at(-1).x},${plot.bottom} L${coordinates[0].x},${plot.bottom} Z`" :fill="`url(#${id}-area)`"/>
        <path v-if="coordinates.length > 1" class="trend-line" :d="path" :stroke="`url(#${id}-line)`" pathLength="1"/>
        <g class="status-pointer" :style="{ transform: `translateX(${active.x}px)` }">
          <line x1="0" x2="0" :y1="plot.top" :y2="plot.bottom"/>
          <circle :cy="active.y" r="5"/>
          <circle class="pointer-core" :cy="active.y" r="2.1"/>
        </g>
        <text v-for="tick in ticks.filter((point) => Math.abs(point.x - active.x) > 34)" :key="`label-${tick.x}`" :x="tick.x" :y="plot.bottom + 17" text-anchor="middle">{{ batteryPointTime(tick, range) }}</text>
        <text class="active-time" :x="active.x" :y="plot.bottom + 17" text-anchor="middle">{{ batteryPointTime(active, range) }}</text>
      </g>
    </svg>
    <div v-if="!coordinates.length" class="trend-empty">尚無電量歷史</div>
    <output v-else class="battery-tooltip" :style="tooltipStyle" aria-live="polite">
      <span class="tooltip-time"><span>{{ tooltipDate }}</span><time>{{ tooltipTime }}</time></span>
      <strong class="tooltip-detail"><span>{{ active.task || '無執行中任務' }} · {{ active.taskId || '—' }}</span><b>電量 {{ Math.round(active.value) }}%</b></strong>
    </output>
  </div>
</template>

<style scoped>
.robot-battery-trend{position:relative;width:100%;height:100%;min-width:0;min-height:105px;background:transparent}.robot-battery-trend svg{display:block;width:100%;height:100%;overflow:hidden}.chart-grid line{stroke:var(--chart-grid);stroke-width:.65}.y-labels text,text{fill:var(--text-muted);font:9px inherit}.trend-line{fill:none;stroke-width:2.1;stroke-linecap:round;stroke-dasharray:1;transition:d 1.2s ease-out;animation:trend-draw 2.9s cubic-bezier(.22,.8,.3,1) both}.trend-area{pointer-events:none;opacity:0;transition:d 1.2s ease-out;animation:trend-area-enter 2.1s ease-out .8s forwards}.status-pointer{pointer-events:none;transition:transform 140ms ease}.status-pointer line{stroke:currentColor;stroke-width:1.15}.status-pointer circle{fill:#fff;stroke:currentColor;stroke-width:1.4;transition:cy 140ms ease}.status-pointer .pointer-core{fill:currentColor;stroke:none}.active-time{fill:var(--text-primary);font-weight:650}.battery-tooltip{position:absolute;display:grid;width:196px;gap:6px;box-sizing:border-box;padding:9px 11px 9px 15px;color:var(--text-primary);background:var(--info-background);border:1px solid var(--glass-border);border-radius:var(--radius-control);box-shadow:var(--info-shadow);backdrop-filter:var(--info-backdrop);pointer-events:none}.battery-tooltip::before{position:absolute;top:5px;bottom:5px;left:3px;width:3px;background:var(--trend-color);border-radius:2px;content:''}.tooltip-time,.tooltip-detail{display:flex;align-items:center;justify-content:space-between;gap:10px;min-width:0}.tooltip-time span,.tooltip-time time{font-size:9.5px;font-variant-numeric:tabular-nums;white-space:nowrap}.tooltip-time time{color:var(--text-secondary)}.tooltip-detail{font-size:10px;font-weight:600;white-space:nowrap}.tooltip-detail span{min-width:0;overflow:hidden;text-overflow:ellipsis}.tooltip-detail b{flex-shrink:0;color:var(--trend-color);font-size:10px;font-weight:700}.trend-empty{position:absolute;inset:0;display:grid;place-items:center;color:var(--text-muted);font-size:11px}.is-large{min-height:360px}.is-large .battery-tooltip{width:232px;padding:10px 12px 10px 16px}.is-large .tooltip-time span,.is-large .tooltip-time time{font-size:11px}.is-large .tooltip-detail,.is-large .tooltip-detail b{font-size:12px}@keyframes trend-draw{from{stroke-dashoffset:1}to{stroke-dashoffset:0}}@keyframes trend-area-enter{to{opacity:1}}svg:focus-visible{outline:1px solid currentColor;outline-offset:-2px}@media(prefers-reduced-motion:reduce){.trend-line,.trend-area{animation:none}.trend-line{stroke-dashoffset:0}.trend-area{opacity:1}.status-pointer,.status-pointer circle{transition:none}}
svg:focus,svg:focus-visible{outline:none}
</style>
