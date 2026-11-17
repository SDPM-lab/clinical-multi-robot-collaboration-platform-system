import { addDays, dayKey } from './scheduleHistory.js'
import { REQUIRED_CAPABILITIES_BY_TASK_TYPE, TASK_TYPE_BY_LABEL } from '@/config/taskTypes.js'
import { robotDisplayCode } from '@/config/robotDisplayCode.js'

// Fixed templates and offsets keep the demo reproducible while showing dates near the viewer's day.
const templates = [
  { title:'廢棄物運送', robotId:'R01', source:'Ward A', destination:'Waste Return', priority:'high' },
  { title:'衣物回收', robotId:'R02', source:'Ward B', destination:'Clothes Return', priority:'urgent' },
  { title:'藥品配送', robotId:'R03', source:'Pharmacy', destination:'Ward A', priority:'normal' },
  { title:'檢體配送', robotId:'R04', source:'Consultation Room 2', destination:'Laboratory', priority:'low' },
  { title:'病房服務', robotId:'R06', source:'Nurse Station', destination:'Ward B', priority:'urgent' },
]
const statuses = ['completed','completed','completed','failed','cancelled','cancelled','completed','completed','completed','completed','failed','completed']
export function createRichDemoHistory(today=dayKey(new Date())) {
  const offsets = [0,0,0,0,-1,-1,-1,-2,-2,-3,-4,-5,-7,-9,-12,-15]
  return offsets.map((offset,index) => {
    const item = templates[index % templates.length]
    const date = addDays(today,offset)
    const hour = 8 + (index % 5) * 2
    const minute = index % 2 ? 20 : 0
    const start = `${date}T${String(hour).padStart(2,'0')}:${String(minute).padStart(2,'0')}:00`
    const duration = 35 + (index % 4) * 15
    const end = new Date(Date.parse(start) + duration * 60000)
    const status = statuses[index % statuses.length]
    const milestones=[-.05,0,.18,.4,.57,1]
    const notes=[item.source,robotDisplayCode(item.robotId),item.source,item.source,item.destination,item.destination]
    const timeline=milestones.map((fraction,stage)=>({time:new Date(Date.parse(start)+duration*60000*fraction).toISOString(),note:notes[stage]}))
    const taskType = TASK_TYPE_BY_LABEL[item.title]
    return { ...item, id:`demo-history-${index+1}`, taskId:`H${String(260901+index).padStart(6,'0')}`, robotName:robotDisplayCode(item.robotId), start, end:end.toISOString(), startLocation:item.source, endLocation:item.destination, status, taskType, requiredCapabilities:[...REQUIRED_CAPABILITIES_BY_TASK_TYPE[taskType]], demo:true, timeline, timelineProgress:status==='completed'?6:status==='running'?4:status==='waiting'?1:status==='cancelled'?2:status==='failed'?5:6 }
  })
}
