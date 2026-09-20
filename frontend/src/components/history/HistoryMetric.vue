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
const {displayed,restart}=useCountUp(computed(()=>props.value??0),{duration:2200,delay:(props.index||0)*70})
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
    <strong class="metric-value">{{value===null?'—':displayed}}</strong>
    <span class="metric-copy">
      <span class="metric-label">{{label}}</span>
      <span class="metric-trend" :data-tone="trendTone"><component :is="trendIcon" :size="13" :stroke-width="1.9" aria-hidden="true"/><b>{{trendAmount}}</b><small>{{trend===0?t('metrics.noChange'):comparisonLabel}}</small></span>
    </span>
    <svg class="metric-sparkline" viewBox="0 0 100 32" preserveAspectRatio="none" aria-hidden="true"><defs><linearGradient :id="gradientId" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--metric-color)" stop-opacity=".16"/><stop offset="1" stop-color="var(--metric-color)" stop-opacity="0"/></linearGradient></defs><path class="spark-area" :d="sparkAreaPath" :fill="`url(#${gradientId})`"/><path class="spark-line" pathLength="1" :d="sparklinePath"/></svg>
    <span class="metric-icon"><component :is="icon" :size="16" :stroke-width="1.8" aria-hidden="true"/></span>
  </button>
</template>

<style scoped>
@property --metric-border-angle{syntax:'<angle>';inherits:false;initial-value:0deg}
.history-metric{--metric-surface:linear-gradient(105deg,rgba(255,255,255,.9),color-mix(in srgb,var(--metric-color) 3%,rgba(255,255,255,.88)));position:relative;isolation:isolate;display:grid;grid-template-columns:58px minmax(0,1fr) 44px;align-items:center;box-sizing:border-box;min-width:0;min-height:105px;width:100%;gap:6px;padding:14px 11px;overflow:hidden;text-align:left;color:var(--text-primary);background:var(--metric-surface) padding-box,conic-gradient(from var(--metric-border-angle),rgba(132,140,136,.2) 0 54%,rgba(184,190,187,.54) 66%,rgba(255,255,255,.96) 74%,rgba(167,174,170,.56) 82%,rgba(132,140,136,.2) 94% 100%) border-box;border:1.25px solid transparent;border-radius:var(--radius-panel);box-shadow:0 1px 0 rgba(255,255,255,.82) inset,0 8px 24px rgba(45,52,58,.055);backdrop-filter:blur(18px) saturate(115%);-webkit-backdrop-filter:blur(18px) saturate(115%);cursor:pointer;animation:metric-border-flow 7.5s linear infinite;transition:box-shadow 180ms ease}
.history-metric:hover{--metric-surface:linear-gradient(105deg,rgba(255,255,255,.94),color-mix(in srgb,var(--metric-color) 5%,rgba(255,255,255,.9)))}
.history-metric.is-selected{--metric-surface:linear-gradient(105deg,rgba(255,255,255,.92),color-mix(in srgb,var(--metric-color) 7%,rgba(255,255,255,.9)));box-shadow:0 1px 0 rgba(255,255,255,.86) inset,0 8px 24px rgba(45,52,58,.055)}
.history-metric:focus-visible{outline:2px solid var(--metric-color);outline-offset:2px}
.metric-icon{position:absolute;top:10px;right:10px;display:grid;width:16px;height:16px;place-items:center;color:var(--metric-color);background:transparent;border:0;box-shadow:none}.metric-copy{display:grid;align-content:center;gap:7px;min-width:0}.metric-label{overflow:hidden;color:var(--text-primary);font-size:15.5px;line-height:1.2;font-weight:650;text-overflow:ellipsis;white-space:nowrap}.metric-value{justify-self:center;color:#252a2c;font-family:"Ubuntu Sans","DejaVu Sans Condensed","Arial Narrow",sans-serif;font-size:47px;line-height:.86;font-weight:600;font-stretch:condensed;font-variant-numeric:tabular-nums;letter-spacing:-.08em}.metric-trend{display:inline-flex;align-items:center;gap:2px;min-width:0;color:var(--text-secondary);font-size:9.5px;white-space:nowrap;font-variant-numeric:tabular-nums}.metric-trend b{font-weight:600}.metric-trend small{min-width:0;margin-left:1px;overflow:hidden;color:inherit;font-size:8.5px;font-weight:400;text-overflow:ellipsis}.metric-trend[data-tone=good]{color:#238d71}.metric-trend[data-tone=bad]{color:#bd5359}.metric-trend[data-tone=flat]{color:var(--text-secondary)}.metric-sparkline{display:block;width:100%;height:36px;margin-top:17px;overflow:visible}.spark-line{fill:none;stroke:var(--metric-color);stroke-width:2;stroke-linecap:round;stroke-linejoin:round;stroke-dasharray:1;stroke-dashoffset:1;vector-effect:non-scaling-stroke;transition:d 1.2s ease-out;animation:metric-line-draw 2.9s cubic-bezier(.22,.8,.3,1) calc(180ms + var(--metric-delay)) forwards}.spark-area{stroke:none;opacity:0;transition:d 1.2s ease-out;animation:metric-area-enter 2.1s ease-out calc(800ms + var(--metric-delay)) forwards}
@keyframes metric-border-flow{to{--metric-border-angle:360deg}}@keyframes metric-line-draw{to{stroke-dashoffset:0}}@keyframes metric-area-enter{to{opacity:1}}
@media(max-width:650px){.history-metric{grid-template-columns:54px minmax(0,1fr) 45px;gap:6px;padding:13px 11px;min-height:101px}.metric-label{font-size:14.5px}.metric-value{font-size:43px}.metric-trend small{font-size:8px}}
@media(prefers-reduced-motion:reduce){.history-metric,.spark-line,.spark-area{animation:none}.spark-line{stroke-dashoffset:0}.spark-area{opacity:1}}
</style>
