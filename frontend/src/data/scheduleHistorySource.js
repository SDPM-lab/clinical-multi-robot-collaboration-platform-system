import { computed } from 'vue'
import { demoFleetStore } from '@/stores/demoFleetStore.js'
import { adaptHistoryTasks } from './scheduleHistory.js'
import { createRichDemoHistory } from './historyDemoData.js'
// Imported on page mount: Loading follows this real module/data initialization promise.
export function createHistorySource() {
 const fallback=createRichDemoHistory()
 return computed(()=>{
  try {
   const actual=adaptHistoryTasks(demoFleetStore.tasks.value,demoFleetStore.robots.value)
   return { events:actual.length?actual:fallback, demo:!actual.length, error:'' }
  } catch { return {events:[],demo:false,error:'無法讀取排程歷史資料。'} }
 })
}
