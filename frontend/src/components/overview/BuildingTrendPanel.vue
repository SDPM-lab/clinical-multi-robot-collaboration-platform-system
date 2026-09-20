<script setup>
import { computed, useId, ref, shallowRef, onMounted, onBeforeUnmount } from 'vue'
import { robotIds } from '@/data/overviewStatusData.js'
const props = defineProps({ history: { type: Object, required: true }, source: { type: String, default: '展示資料' } })
const root = ref(null)
const plotSize = shallowRef({ width: 300, height: 180 })
const baseline = computed(() => plotSize.value.height - 24)
const chartY = value => baseline.value - value * (plotSize.value.height - 36) / 100
const plotLeft = 36
const plotRight = 12
const barGap = 3
const barWidth = computed(() => Math.max(7, Math.min(12, (plotSize.value.width - plotLeft - plotRight) / 5 / 4.5)))
let observer
onMounted(() => {
  const svg = root.value?.querySelector('svg')
  if (!svg || typeof ResizeObserver === 'undefined') return
  observer = new ResizeObserver(([entry]) => {
    const width = Math.round(entry.contentRect.width), height = Math.round(entry.contentRect.height)
    if (width > 0 && height > 0 && (width !== plotSize.value.width || height !== plotSize.value.height)) plotSize.value = { width, height }
  })
  observer.observe(svg)
})
onBeforeUnmount(() => observer?.disconnect())
const colors = ['#E88746', '#D5AD4E', '#55AF91']
const gradientTops = ['#F4B26D', '#E8CE72', '#93CFB9']
const gradientBottoms = ['#D96F31', '#C99E34', '#439B80']
const gradientPrefix = `battery-${useId().replace(/:/g, '')}`
const charts = computed(() => ['floor1','floor2','floor3'].map((floorId, floorIndex) => {
  const rows = (props.history[floorId] || []).slice(-5)
  const points = rows.map((row, index) => ({
    time: row.time,
    values: robotIds.map(id => Number.isFinite(row.batteries?.[id]) ? Math.max(0, Math.min(100, row.batteries[id])) : null),
    x: plotLeft + (index + .5) * (plotSize.value.width - plotLeft - plotRight) / Math.max(1, rows.length),
  }))
  return { floorId, floorIndex, points }
}))
</script>
<template>
  <div ref="root" class="building-trend-panel" :style="{'--plot-baseline':`${baseline}px`}">
    <div class="building-trend-legend"><h2>全棟電量趨勢</h2><small>{{ source }}</small><span v-for="(id,i) in robotIds" :key="id"><i :style="{background:colors[i]}"></i>Robot 0{{ i+1 }}</span></div>
    <section v-for="chart in charts" :key="chart.floorId" class="floor-chart" :style="{'--floor-index':chart.floorIndex}">
      <header><span class="floor-label">Floor {{ chart.floorIndex+1 }}</span><small>電量 (%)</small></header>
      <svg :viewBox="`0 0 ${plotSize.width} ${plotSize.height}`" role="img" :aria-label="`Floor ${chart.floorIndex+1} 每小時電量趨勢`">
        <defs>
          <linearGradient v-for="(id,i) in robotIds" :id="`${gradientPrefix}-${chart.floorId}-${i}`" :key="id" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" :stop-color="gradientTops[i]"/><stop offset="100%" :stop-color="gradientBottoms[i]"/>
          </linearGradient>
        </defs>
        <g class="chart-axes"><g v-for="tick in [0,50,100]" :key="tick"><line :x1="plotLeft" :x2="plotSize.width-plotRight+2" :y1="chartY(tick)" :y2="chartY(tick)"/><text :x="plotLeft-6" :y="chartY(tick)+3" text-anchor="end">{{tick}}</text></g></g>
        <g v-for="(point,index) in chart.points" :key="point.time">
          <g v-for="(value,robotIndex) in point.values" :key="robotIndex"><rect v-if="value !== null" class="robot-bar" :x="point.x+(robotIndex-1)*(barWidth+barGap)-barWidth/2" :y="chartY(value)" :width="barWidth" :height="baseline-chartY(value)" :fill="`url(#${gradientPrefix}-${chart.floorId}-${robotIndex})`" :style="{'--bar-index':robotIndex,'--hour-index':index}"><title>{{ point.time }} Robot 0{{robotIndex+1}}：{{value}}%</title></rect></g>
          <text :x="point.x" :y="plotSize.height-7" text-anchor="middle">{{ point.time }}</text>
        </g>
        <text v-if="!chart.points.length" x="140" y="50" text-anchor="middle">尚無歷史資料</text>
      </svg>
    </section>
  </div>
</template>
<style scoped>
.building-trend-panel{display:grid;grid-template-columns:90px repeat(3,minmax(0,1fr));height:100%;min-height:0;grid-template-rows:minmax(0,1fr);padding:10px 14px;gap:6px}.building-trend-legend{width:90px;min-width:90px;display:grid;align-content:center;gap:7px}.building-trend-legend h2{margin:0;color:#454b48;font-size:13.5px;font-weight:600;line-height:1.25;display:flex;align-items:center;gap:5px}.building-trend-legend small{font-size:10px;color:#929794}.building-trend-legend span{display:flex;gap:7px;align-items:center;font-size:10px;color:#737977}.building-trend-legend i{width:7px;height:7px;border-radius:50%}.floor-chart{min-width:0;min-height:0;display:grid;grid-template-rows:21px minmax(0,1fr);border-left:1px solid rgba(90,100,96,.1);padding-left:4px;animation:dashboard-fade 450ms ease calc(560ms + var(--floor-index)*100ms) both}.floor-chart header{display:flex;align-items:flex-start;justify-content:space-between;padding:0 3px;font-size:11px}.floor-chart .floor-label{display:inline-flex;align-items:center;height:17px;padding:0 6px;color:#9a672f;font-size:11px;font-weight:550;background:linear-gradient(110deg,rgba(242,174,82,.15),rgba(255,241,207,.3));border:1px solid rgba(218,143,57,.22);border-radius:4px}.floor-chart:nth-of-type(3) .floor-label{background:linear-gradient(125deg,rgba(237,165,76,.13),rgba(255,235,194,.27))}.floor-chart:nth-of-type(4) .floor-label{background:linear-gradient(140deg,rgba(224,151,68,.12),rgba(252,230,190,.25))}.floor-chart header small{padding-top:2px;color:#737b77;font-size:9.5px}.floor-chart svg{display:block;width:100%;height:100%;min-height:0;overflow:hidden}text{fill:#858b88;font-size:10px;font-family:inherit}.chart-axes{animation:dashboard-fade 350ms ease 600ms both}.chart-axes line{stroke:#cdd2d0;stroke-width:.5}.robot-bar{transition:y 1.2s ease-out,height 1.2s ease-out;transform-box:view-box;transform-origin:0 var(--plot-baseline);animation:bar-grow 2.2s cubic-bezier(.22,.8,.3,1) calc(420ms + var(--bar-index)*100ms + var(--floor-index)*100ms + var(--hour-index)*100ms) both}@keyframes bar-grow{from{transform:scaleY(0)}to{transform:scaleY(1)}}
.building-trend-panel,.floor-chart,.floor-chart svg{background:transparent}.floor-chart{padding:0 10px 0 10px}.floor-chart text{font-size:9.5px}.chart-axes text{font-size:9px;font-variant-numeric:tabular-nums}
@media(prefers-reduced-motion:reduce){.robot-bar,.floor-chart,.chart-axes{animation:none}}
</style>
