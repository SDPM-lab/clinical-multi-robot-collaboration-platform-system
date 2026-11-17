<script setup>
import { computed } from 'vue'
import { Ban, CircleCheck, ClipboardList, TriangleAlert } from '@lucide/vue'
import { historyStatusColors, summarizeHistory } from '@/data/historyPresentation.js'
import { t } from '@/i18n/index.js'
import HistoryMetric from './HistoryMetric.vue'

const props=defineProps({
  events:{type:Array,default:()=>[]},
  previousEvents:{type:Array,default:()=>[]},
  period:{type:String,default:'weekly'},
  selectedStatus:{type:String,default:'all'},
  rangeStart:{type:String,default:''},
})
const emit=defineEmits(['select'])
const values=computed(()=>summarizeHistory(props.events))
const previous=computed(()=>summarizeHistory(props.previousEvents))
const metrics=Object.freeze([
  {key:'total',filter:'all',icon:ClipboardList},
  {key:'completed',filter:'completed',icon:CircleCheck},
  {key:'cancelled',filter:'cancelled',icon:Ban},
  {key:'failed',filter:'failed',icon:TriangleAlert},
])
const seriesFor = metric => {
  const anchor = props.rangeStart ? new Date(`${props.rangeStart}T00:00:00`) : new Date(props.events[0]?.start || Date.now())
  anchor.setHours(0,0,0,0)
  const count = props.period === 'daily' ? 24 : props.period === 'monthly' ? new Date(anchor.getFullYear(),anchor.getMonth()+1,0).getDate() : 7
  const values = Array(count).fill(0)
  for (const event of props.events) {
    if (metric.filter !== 'all' && event.status !== metric.filter) continue
    const date = new Date(event.start)
    const index = props.period === 'daily' ? date.getHours() : Math.round((Date.UTC(date.getFullYear(),date.getMonth(),date.getDate())-Date.UTC(anchor.getFullYear(),anchor.getMonth(),anchor.getDate()))/86400000)
    if (index >= 0 && index < count) values[index]++
  }
  return values
}
const comparisonLabel=computed(()=>t(`metrics.${({daily:'vsDay',weekly:'vsWeek',monthly:'vsMonth'}[props.period]||'vsDay')}`))
</script>

<template>
  <div class="history-summary" :aria-label="t('history.taskCount')">
    <HistoryMetric
      v-for="(metric,index) in metrics"
      :key="metric.key"
      :index="index"
      :label="t(`metrics.${metric.key}`)"
      :value="values[metric.key]"
      :trend="values[metric.key]-previous[metric.key]"
      :comparison-label="comparisonLabel"
      :icon="metric.icon"
      :series="seriesFor(metric)"
      :color="historyStatusColors[metric.filter]"
      :status="metric.filter"
      :selected="selectedStatus===metric.filter"
      @select="emit('select',metric.filter)"
    />
  </div>
</template>

<style scoped>
.history-summary{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));grid-auto-rows:82px;gap:12px;min-width:0;flex:none}
@media(max-width:900px){.history-summary{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media(max-width:580px){.history-summary{grid-template-columns:repeat(2,minmax(0,1fr))}}
</style>
