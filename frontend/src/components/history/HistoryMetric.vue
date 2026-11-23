<script setup>
import { computed, onMounted } from 'vue'
import { ArrowDown, ArrowRight, ArrowUp } from '@lucide/vue'
import { useCountUp } from '@/composables/useCountUp.js'
import { t } from '@/i18n/index.js'

const props=defineProps({
  label:String,
  value:Number,
  color:String,
  status:String,
  index:Number,
  icon:[Object,Function],
  series:{type:Array,default:()=>[]},
  trend:{type:Number,default:0},
  comparisonLabel:String,
  selected:Boolean,
})
const emit=defineEmits(['select'])
const {displayed,restart}=useCountUp(computed(()=>props.value??0),{duration:850,delay:(props.index||0)*45})
onMounted(restart)
const trendIcon=computed(()=>props.trend>0?ArrowUp:props.trend<0?ArrowDown:ArrowRight)
const trendTone=computed(()=>props.trend>0?'good':props.trend<0?'bad':'flat')
const trendAmount=computed(()=>`${props.trend>0?'+':''}${props.trend}`)
const sparkPoints=computed(()=>{
  const values=props.series.length?props.series:[0,0]
  const min=Math.min(...values),max=Math.max(...values),span=Math.max(1,max-min)
  return values.map((value,index)=>({x:index*100/Math.max(1,values.length-1),y:28-(value-min)*22/span}))
})
const sparklinePath=computed(()=>{
  const points=sparkPoints.value
  return points.slice(1).reduce((path,point,index)=>{
    const previous=points[index],middle=(previous.x+point.x)/2
    return `${path} C ${middle} ${previous.y}, ${middle} ${point.y}, ${point.x} ${point.y}`
  },`M ${points[0].x} ${points[0].y}`)
})
const sparkAreaPath=computed(()=>`${sparklinePath.value} L 100 32 L 0 32 Z`)
const gradientId=computed(()=>`metric-spark-${props.status}`)
</script>

<template>
  <button
    type="button"
    class="history-metric"
    :class="{'is-selected':selected}"
    :data-status="status"
    :aria-pressed="selected"
    :aria-label="`${label} ${value??'—'}; ${trendAmount} ${trend===0?t('metrics.noChange'):comparisonLabel}`"
    :style="{'--metric-color':color,'--metric-delay':`${(index||0)*90}ms`}"
    @click="emit('select')"
  >
    <span class="metric-top">
      <span class="metric-label">{{label}}</span>
      <span class="metric-icon"><component :is="icon" :size="16" :stroke-width="1.8" aria-hidden="true"/></span>
    </span>
    <span class="history-metric-reading">
      <strong class="metric-value">{{value===null?'—':displayed}}</strong>
      <span class="metric-trend" :data-tone="trendTone"><component :is="trendIcon" :size="13" :stroke-width="1.9" aria-hidden="true"/><b>{{trendAmount}}</b><small>{{trend===0?t('metrics.noChange'):comparisonLabel}}</small></span>
    </span>
    <svg class="metric-sparkline" viewBox="0 0 100 32" preserveAspectRatio="none" aria-hidden="true"><defs><linearGradient :id="gradientId" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--metric-color)" stop-opacity=".16"/><stop offset="1" stop-color="var(--metric-color)" stop-opacity="0"/></linearGradient></defs><path class="spark-area" :d="sparkAreaPath" :fill="`url(#${gradientId})`"/><path class="spark-line" pathLength="1" :d="sparklinePath"/></svg>
  </button>
</template>

<style scoped>
@property --history-metric-angle{syntax:'<angle>';inherits:false;initial-value:0deg}
@keyframes history-metric-border-flow{to{--history-metric-angle:360deg}}
.history-metric{position:relative;display:flex;flex-direction:column;align-items:flex-start;box-sizing:border-box;min-width:0;width:100%;height:var(--history-metric-height, 88px);min-height:var(--history-metric-height, 88px);padding:8px 15px;overflow:hidden;text-align:left;color:var(--text-primary);background:var(--panel-bg-strong);border:1px solid var(--panel-border);border-radius:14px;box-shadow:0 8px 24px #25322b0b;cursor:pointer;transition:background 180ms ease,border-color 180ms ease,box-shadow 180ms ease}
.history-metric:hover{background:color-mix(in srgb,var(--metric-color) 10%,var(--panel-bg-strong));border-color:color-mix(in srgb,var(--metric-color) 22%,var(--panel-border));box-shadow:0 10px 26px #25322b14}
.history-metric.is-selected{background:color-mix(in srgb,var(--metric-color) 7%,var(--panel-bg-strong));border-color:color-mix(in srgb,var(--metric-color) 28%,var(--panel-border));box-shadow:0 8px 24px #25322b0b}
.history-metric.is-selected::before{position:absolute;inset:0;padding:2px;border-radius:inherit;background:conic-gradient(from var(--history-metric-angle),transparent 0deg,color-mix(in srgb,var(--metric-color) 90%,white) 48deg,var(--metric-color) 80deg,transparent 126deg,transparent 360deg);-webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);-webkit-mask-composite:xor;mask-composite:exclude;content:'';pointer-events:none;animation:history-metric-border-flow 2.8s linear infinite}
.history-metric:focus-visible{outline:2px solid var(--metric-color);outline-offset:2px}
.metric-top{display:flex;align-items:center;justify-content:space-between;gap:6px;width:100%}.metric-label{overflow:hidden;color:var(--text-secondary);font-size:13px;font-weight:650;letter-spacing:.02em;text-overflow:ellipsis;white-space:nowrap}.metric-icon{display:grid;flex:none;width:23px;height:23px;place-items:center;color:var(--metric-color);background:color-mix(in srgb,var(--metric-color) 10%,var(--panel-bg-strong));border-radius:7px}
.history-metric-reading{display:flex;align-items:center;gap:10px;width:100%;min-width:0;margin-top:auto;margin-bottom:2px}
.metric-value{flex:none;color:var(--text-primary);font-size:42px;font-weight:700;line-height:1;letter-spacing:-.04em;font-variant-numeric:tabular-nums}.metric-trend{display:inline-flex;align-items:center;gap:3px;min-width:0;color:var(--text-secondary);font-size:11px;white-space:nowrap;font-variant-numeric:tabular-nums}.metric-trend svg{flex:none}.metric-trend b{flex:none;font-weight:650}.metric-trend small{overflow:hidden;margin-left:2px;color:var(--text-muted);font-size:11px;text-overflow:ellipsis}.metric-trend[data-tone=good]{color:#5b9678}.metric-trend[data-tone=bad]{color:#bd756a}
.metric-sparkline{display:none}.spark-line{fill:none;stroke:var(--metric-color);stroke-width:1.6;stroke-linecap:round;stroke-linejoin:round;vector-effect:non-scaling-stroke}.spark-area{opacity:.6}
@media(max-width:650px){.history-metric{padding:8px 12px}.metric-value{font-size:36px}.metric-label{font-size:11px}}
@media(prefers-reduced-motion:reduce){.history-metric.is-selected::before{animation:none;background:color-mix(in srgb,var(--metric-color) 70%,transparent)}}
</style>
