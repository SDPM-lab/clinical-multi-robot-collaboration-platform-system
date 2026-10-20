import { addDays, dayKey } from './scheduleHistory.js'
import { REQUIRED_CAPABILITIES_BY_TASK_TYPE, TASK_TYPE_BY_LABEL } from '@/config/taskTypes.js'

// Fixed templates and offsets keep the demo reproducible while showing dates near the viewer's day.
const templates = [
  { title:'藥品配送', robotId:'R01', origin:'Pharmacy', destination:'Nurse Reception', priority:'high', routeCoordinates:[[180,330],[300,320],[405,265],[530,270]] },
  { title:'檢體配送', robotId:'R02', origin:'Consultation Room 2', destination:'Laboratory', priority:'urgent', routeCoordinates:[[570,440],[505,370],[365,370],[250,270]] },
  { title:'一般配送', robotId:'R03', origin:'Nurse Station', destination:'Ward A', priority:'normal', routeCoordinates:[[450,230],[475,290],[620,310],[690,365]] },
  { title:'一般配送', robotId:'R01', origin:'Nurse Reception', destination:'Consultation Room 2', priority:'low', routeCoordinates:[[530,270],[490,330],[560,390],[570,440]] },
  { title:'廢棄物收集', robotId:'R03', origin:'Ward A', destination:'Waste Return', priority:'urgent' },
  { title:'一般配送', robotId:'R02', origin:'Charging Station A', destination:'Nurse Station', priority:'normal', routeCoordinates:[[310,500],[350,385],[430,315],[450,230]] },
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
    const notes=[item.origin,`Robot ${item.robotId.slice(1)}`,item.origin,item.origin,item.destination,item.destination]
    const timeline=milestones.map((fraction,stage)=>({time:new Date(Date.parse(start)+duration*60000*fraction).toISOString(),note:notes[stage]}))
    const taskType = TASK_TYPE_BY_LABEL[item.title]
    return { ...item, id:`demo-history-${index+1}`, taskId:`H${String(260901+index).padStart(6,'0')}`, robotName:`Robot ${item.robotId.slice(1)}`, start, end:end.toISOString(), startLocation:item.origin, endLocation:item.destination, status, taskType, requiredCapabilities:[...REQUIRED_CAPABILITIES_BY_TASK_TYPE[taskType]], demo:true, timeline, timelineProgress:status==='completed'?6:status==='running'?4:status==='waiting'?1:status==='cancelled'?2:status==='failed'?5:6 }
  })
}
