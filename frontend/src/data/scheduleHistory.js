import { locationDetails } from './demoActiveRoutes.js'
export const priorityOptions = [{id:'urgent',label:'緊急',from:'#f06a50',to:'#ff9a62'},{id:'high',label:'高',from:'#ed8b2c',to:'#ffc061'},{id:'normal',label:'一般',from:'#f2bd43',to:'#f6dc79'},{id:'low',label:'低',from:'#70b99c',to:'#a4d6b9'}]
export const statusOptions = [{id:'completed',label:'已完成'},{id:'cancelled',label:'已取消'},{id:'failed',label:'失敗'},{id:'running',label:'執行中'},{id:'waiting',label:'等待中'}]
export const historyLocations = Object.values(locationDetails).map(location=>location.label)
export const dayKey = date => `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`
export const parseDay = key => new Date(`${key}T00:00:00`)
export const addDays = (key,amount) => { const date=parseDay(key);date.setDate(date.getDate()+amount);return dayKey(date) }
export const weekStart = key => addDays(key,-((parseDay(key).getDay()+6)%7))
export function monthDays(key) {
 const date=parseDay(key);date.setDate(1)
 const start=weekStart(dayKey(date))
 return Array.from({length:42},(_,i)=>addDays(start,i))
}
export function historyRange(key,view) {
 if(view==='daily') return [key,addDays(key,1)]
 if(view==='weekly'){const start=weekStart(key);return [start,addDays(start,7)]}
 const date=parseDay(key);date.setDate(1);const start=dayKey(date);date.setMonth(date.getMonth()+1);return [start,dayKey(date)]
}
export function filterHistory(events,filters,search='') {
 const query=search.trim().toLowerCase()
 return events.filter(event=>Object.entries(filters).every(([field,values])=>!values.length || (field==='location'?values.includes(event.startLocation)||values.includes(event.endLocation):values.includes(event[field]))) && (!query || [event.taskId,event.title,event.robotId,event.robotName,event.startLocation,event.endLocation].join(' ').toLowerCase().includes(query)))
}
export function eventsOnDay(events,key) {
 const start=parseDay(key).getTime(),end=parseDay(addDays(key,1)).getTime()
 return events.filter(event=>Date.parse(event.start)<end && Date.parse(event.end)>start)
}
// Split cross-midnight records for display and allocate separate overlap lanes.
export function layoutDayEvents(events,key) {
 const dayStart=parseDay(key).getTime(),dayEnd=parseDay(addDays(key,1)).getTime()
 const rows=eventsOnDay(events,key).map(event=>({event,start:Math.max(Date.parse(event.start),dayStart),end:Math.min(Date.parse(event.end),dayEnd)})).sort((a,b)=>a.start-b.start||b.end-a.end)
 let group=[],groupEnd=0
 const flush=()=>{const ends=[];for(const row of group){let lane=ends.findIndex(end=>end<=row.start);if(lane<0)lane=ends.length;ends[lane]=row.end;row.lane=lane}for(const row of group)row.lanes=ends.length;group=[]}
 for(const row of rows){if(group.length&&row.start>=groupEnd)flush();group.push(row);groupEnd=Math.max(groupEnd,row.end)}flush()
 return rows.map(row=>({...row,top:(row.start-dayStart)/3600000*76,height:Math.max(22,(row.end-row.start)/3600000*76)}))
}
export function adaptHistoryTasks(tasks,robots) {
 const statuses={completed:'completed',done:'completed',cancelled:'cancelled',failed:'failed',error:'failed',executing:'running',running:'running',waiting:'waiting'}
 return tasks.flatMap(task=>{
  const start=task.start || (task.date ? `${task.date}T${task.startTime}` : null)
  const end=task.end || (task.date ? `${task.date}T${task.endTime}` : null)
  if(!statuses[task.status] || !Number.isFinite(Date.parse(start)) || !(Date.parse(end)>Date.parse(start)))return []
  return [{id:task.id,taskId:task.taskId||task.id,title:task.title,robotId:task.robotId,robotName:robots.find(robot=>robot.id===task.robotId)?.name||task.robotId,start,end,startLocation:task.origin||task.startLocation,endLocation:task.destination||task.endLocation,priority:task.priority||'normal',status:statuses[task.status],taskType:task.taskType||task.title}]
 })
}
// Explicit demo history, generated once from existing task templates; never persisted as real history.
export function createDemoHistory(tasks,robots,today=dayKey(new Date())) {
 const start=weekStart(today),events=[]
 for(let day=-14;day<14;day++) {
  const date=addDays(start,day)
  if(date>today)continue
  tasks.slice(0,3).forEach((task,index)=>{
   const hour=9+index*3+(Math.abs(day)%2),minutes=index===1?15:0
   const begin=new Date(`${date}T${String(hour).padStart(2,'0')}:${String(minutes).padStart(2,'0')}:00`)
   const end=new Date(begin.getTime()+(50+((day+14)%3)*15)*60000)
   const priority=priorityOptions[(day+14+index)%4].id
   events.push({id:`history-${date}-${task.id}`,taskId:`H${String((day+14)*3+index+1).padStart(4,'0')}`,title:task.title,robotId:task.robotId,robotName:robots.find(robot=>robot.id===task.robotId)?.name||task.robotId,start:begin.toISOString(),end:end.toISOString(),startLocation:task.origin,endLocation:task.destination,priority,status:date===today&&index===1?'running':(day+14+index)%13===0?'failed':(day+14+index)%11===0?'cancelled':'completed',taskType:task.title})
  })
 }
 return events
}
