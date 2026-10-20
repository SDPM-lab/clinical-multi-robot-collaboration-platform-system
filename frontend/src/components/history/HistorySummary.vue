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
})
const emit=defineEmits(['select'])
const values=computed(()=>summarizeHistory(props.events))
const previous=computed(()=>summarizeHistory(props.previousEvents))
const metrics=Object.freeze([
  {key:'total',filter:'all',icon:ClipboardList,series:[4,5,4,7,6,8,9]},
  {key:'completed',filter:'completed',icon:CircleCheck,series:[2,3,3,4,3,5,5]},
  {key:'cancelled',filter:'cancelled',icon:Ban,series:[2,1,2,1,1,2,1]},
  {key:'failed',filter:'failed',icon:TriangleAlert,series:[0,1,0,2,1,1,1]},
])
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
      :series="metric.series"
      :color="historyStatusColors[metric.filter]"
      :status="metric.filter"
      :selected="selectedStatus===metric.filter"
      @select="emit('select',metric.filter)"
    />
  </div>
</template>

<style scoped>
.history-summary{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;min-width:0;flex:none}
@media(max-width:900px){.history-summary{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media(max-width:580px){.history-summary{grid-template-columns:repeat(2,minmax(0,1fr))}}
</style>
