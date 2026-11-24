<script setup>
import { getRobotVisualTheme } from '@/config/robotVisualThemes.js'
import { computed, useId, ref, shallowRef, onMounted, onBeforeUnmount } from 'vue'
import { robotIds } from '@/data/overviewStatusData.js'
import { t } from '@/i18n/index.js'
const props = defineProps({ history: { type: Object, required: true } })
const root = ref(null)
const plotSize = shallowRef({ width: 300, height: 180 })
const baseline = computed(() => plotSize.value.height - 32)
const chartY = value => baseline.value - value * (plotSize.value.height - 44) / 100
const plotLeft = 36
const plotRight = 12
const barGap = 1
const barWidth = computed(() => Math.max(2, Math.min(7, ((plotSize.value.width - plotLeft - plotRight) / 5 - 10) / 7)))
let observer
onMounted(() => {
  const svg = root.value?.querySelector('.floor-chart svg')
  if (!svg || typeof ResizeObserver === 'undefined') return
  observer = new ResizeObserver(([entry]) => {
    const width = Math.round(entry.contentRect.width), height = Math.round(entry.contentRect.height)
    if (width > 0 && height > 0 && (width !== plotSize.value.width || height !== plotSize.value.height)) plotSize.value = { width, height }
  })
  observer.observe(svg)
})
onBeforeUnmount(() => observer?.disconnect())
const colors = robotIds.map(id => getRobotVisualTheme(id).main)
const gradientTops = colors
const gradientBottoms = colors
const gradientPrefix = `battery-${useId().replace(/:/g, '')}`
const charts = computed(() => ['floor1','floor2','floor3'].map((floorId, floorIndex) => {
  const rows = (props.history[floorId] || []).slice(-5)
  const points = rows.map((row, index) => ({
    time: row.time,
    observedTimes: row.observedTimes || {},
    values: robotIds.map(id => Number.isFinite(row.batteries?.[id]) ? Math.max(0, Math.min(100, row.batteries[id])) : null),
    x: plotLeft + (index + .5) * (plotSize.value.width - plotLeft - plotRight) / Math.max(1, rows.length),
  }))
  return { floorId, floorIndex, points }
}))
</script>
<template>
  <div ref="root" class="building-trend-panel" :style="{'--plot-baseline':`${baseline}px`}">
    <header class="building-trend-heading"><div><h2>全棟電量趨勢</h2><small>{{ t('dashboard.observedBatteryHistory') }}</small></div>
      <div class="chart-legend" aria-label="機器人圖例"><span v-for="(id,i) in robotIds" :key="id"><i :style="{background:colors[i]}"></i>{{ id }}</span></div>
    </header>
    <section v-for="chart in charts" :key="chart.floorId" class="floor-chart" :style="{'--floor-index':chart.floorIndex}">
      <header><span class="floor-label">{{ t('dashboard.floor', { number: chart.floorIndex + 1 }) }}</span><small>電量 (%)</small></header>
      <svg :viewBox="`0 0 ${plotSize.width} ${plotSize.height}`" role="img" :aria-label="t('dashboard.hourlyBatteryTrend', { number: chart.floorIndex + 1 })">
        <defs>
          <linearGradient v-for="(id,i) in robotIds" :id="`${gradientPrefix}-${chart.floorId}-${i}`" :key="id" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" :stop-color="gradientTops[i]" stop-opacity=".72"/><stop offset="100%" :stop-color="gradientBottoms[i]"/>
          </linearGradient>
        </defs>
        <g class="chart-axes"><g v-for="tick in [0,50,100]" :key="tick"><line :x1="plotLeft" :x2="plotSize.width-plotRight+2" :y1="chartY(tick)" :y2="chartY(tick)"/><text :x="plotLeft-6" :y="chartY(tick)+3" text-anchor="end">{{tick}}</text></g></g>
        <g v-for="(point,index) in chart.points" :key="point.time">
          <g v-for="(value,robotIndex) in point.values" :key="robotIndex"><rect v-if="value !== null" class="robot-bar" :x="point.x+(robotIndex-3)*(barWidth+barGap)-barWidth/2" :y="chartY(value)" :width="barWidth" :height="baseline-chartY(value)" :fill="`url(#${gradientPrefix}-${chart.floorId}-${robotIndex})`" :style="{'--bar-index':robotIndex,'--hour-index':index}"><title>{{ point.observedTimes[robotIds[robotIndex]] || point.time }} {{ robotIds[robotIndex] }}：{{value}}%</title></rect></g>
          <text v-if="index % Math.max(1, Math.ceil(42 * chart.points.length / (plotSize.width - plotLeft - plotRight))) === 0" :x="point.x" :y="baseline + 16" text-anchor="middle" class="time-label">{{ point.time }}</text>
        </g>
        <text v-if="!chart.points.length" x="140" y="50" text-anchor="middle">尚無歷史資料</text>
      </svg>
    </section>
  </div>
</template>
<style scoped>
.building-trend-panel{box-sizing:border-box;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));height:100%;min-height:0;grid-template-rows:auto minmax(0,1fr);padding:14px 16px 20px;gap:10px}.floor-chart{min-width:0;min-height:0;display:grid;grid-template-rows:23px minmax(0,1fr);border-left:1px solid var(--overview-divider);padding-left:7px;animation:dashboard-fade 450ms ease calc(560ms + var(--floor-index)*100ms) both}.floor-chart header{display:flex;align-items:flex-start;justify-content:space-between;padding:0 4px;font-size:11px}.floor-chart .floor-label{display:inline-flex;align-items:center;height:19px;padding:0 5px;color:var(--overview-accent-text);font-size:11px;font-weight:550;background:var(--theme-primary-soft);border:1px solid rgba(var(--overview-accent-rgb),.16);border-radius:var(--radius-control)}.floor-chart:nth-of-type(3) .floor-label,.floor-chart:nth-of-type(4) .floor-label{background:var(--theme-primary-soft)}.floor-chart header small{padding-top:2px;color:var(--text-secondary);font-size:9px}.floor-chart svg{display:block;width:100%;height:100%;min-height:0;overflow:hidden}text{fill:var(--text-muted);font-size:10px;font-family:inherit}.time-label{font-size:8px;fill:var(--text-muted)}.chart-axes{animation:dashboard-fade 350ms ease 600ms both}.chart-axes line{stroke:var(--chart-grid);stroke-width:.5;opacity:.5}.robot-bar{transition:y 1.2s ease-out,height 1.2s ease-out;transform-box:view-box;transform-origin:0 var(--plot-baseline);animation:bar-grow 2.2s cubic-bezier(.22,.8,.3,1) calc(420ms + var(--bar-index)*100ms + var(--floor-index)*100ms + var(--hour-index)*100ms) both}@keyframes bar-grow{from{transform:scaleY(0)}to{transform:scaleY(1)}}
.building-trend-panel,.floor-chart,.floor-chart svg{background:transparent}.floor-chart{padding:0 3px}.floor-chart text{font-size:9px}.chart-axes text{font-size:8.5px;font-variant-numeric:tabular-nums}
.building-trend-heading{grid-column:1/-1;display:flex;align-items:center;justify-content:space-between;gap:8px;min-width:0}.building-trend-heading h2{margin:0;font-size:13px;font-weight:500;white-space:nowrap}.building-trend-heading small{display:block;margin-top:4px;color:var(--text-muted);font-size:9px}.floor-chart:nth-of-type(1){border-left:0}
.chart-legend{display:flex;flex-wrap:wrap;justify-content:center;gap:4px 10px;padding:4px 0 8px}.chart-legend span{display:inline-flex;align-items:center;gap:4px;white-space:nowrap;font-size:9px;color:var(--text-secondary)}.chart-legend i{width:5px;height:5px;border-radius:50%;flex-shrink:0}
@media(prefers-reduced-motion:reduce){.robot-bar,.floor-chart,.chart-axes{animation:none}}
@media(max-width:1200px){.building-trend-heading{align-items:flex-start;flex-direction:column}.chart-legend{justify-content:flex-start;padding:0}}
@media(max-width:1100px){.building-trend-panel{grid-template-columns:minmax(0,1fr);grid-template-rows:auto repeat(3,150px);overflow-y:auto;scrollbar-width:thin;scrollbar-color:rgba(var(--overview-accent-rgb),.35) transparent}.floor-chart{border-left:0;border-top:1px solid var(--overview-divider);padding-top:6px}}
@media(min-width:701px) and (max-width:1100px) and (orientation:landscape){.building-trend-panel{grid-template-columns:repeat(3,minmax(0,1fr));grid-template-rows:auto minmax(0,1fr);overflow:hidden}.floor-chart{border-top:0;border-left:1px solid var(--overview-divider);padding-top:0}.floor-chart:nth-of-type(1){border-left:0}}
h2{display:flex;align-items:center;gap:7px}h2 svg{flex:none;color:var(--theme-primary)}
</style>
