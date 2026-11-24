import { afterEach, expect, it, vi } from 'vitest'
import { createHistorySource } from '@/data/scheduleHistorySource.js'
import { taskApi } from '@/services/taskApi.js'
import { adaptBackendHistoryTasks, eventsOnDay } from '@/data/scheduleHistory.js'
afterEach(()=>vi.restoreAllMocks())
const task={id:'uuid-1',taskCode:'T0001',taskType:'medication_delivery',source:'pharmacy',destination:'reception_back',priority:'emergency',status:'completed',assignedRobot:'robot-a',scheduledAt:'2026-10-25T09:30:00+08:00',startedAt:'2026-10-25T09:35:00+08:00',finishedAt:'2026-10-25T09:50:00+08:00',createdAt:'2026-10-25T08:00:00+08:00',requiredCapabilities:['navigation','medication_delivery'],note:'Handoff'}
it('loads real tasks and maps fields without changing the internal ID',async()=>{
 vi.spyOn(taskApi,'getTaskRecords').mockResolvedValue([task,{...task,id:'pending',status:'pending'}])
 vi.spyOn(taskApi,'getRobots').mockResolvedValue([{id:'robot-a',name:'Robot A'}])
 const source=await createHistorySource()
 expect(source.value.demo).toBe(false)
 expect(source.value.robots).toEqual([{id:'robot-a',name:'Robot A'}])
 expect(source.value.events).toHaveLength(1)
 expect(source.value.events[0]).toMatchObject({id:'uuid-1',taskId:'T0001',title:'藥品配送',robotName:'C01',startLocation:'Pharmacy',endLocation:'Nurse Reception',priority:'urgent',delayMinutes:5,durationMinutes:15,requiredCapabilities:['navigation','medication_delivery']})
})
it('keeps missing actual times null rather than copying scheduled time',()=>{
 const [event]=adaptBackendHistoryTasks([{...task,status:'cancelled',startedAt:null,finishedAt:null}])
 expect(event.startedAt).toBeNull()
 expect(event.finishedAt).toBeNull()
 expect(event.delayMinutes).toBeNull()
 expect(event.durationMinutes).toBeNull()
 const date=new Date(task.scheduledAt)
 const key=`${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`
 expect(eventsOnDay([event],key)).toHaveLength(1)
})
it('does not generate demo history when the API returns no tasks',async()=>{
 vi.spyOn(taskApi,'getTaskRecords').mockResolvedValue([])
 vi.spyOn(taskApi,'getRobots').mockResolvedValue([])
 expect((await createHistorySource()).value.events).toEqual([])
})
it('propagates load errors for the page retry state',async()=>{
 vi.spyOn(taskApi,'getTaskRecords').mockRejectedValue(new Error('Unavailable'))
 vi.spyOn(taskApi,'getRobots').mockResolvedValue([])
 await expect(createHistorySource()).rejects.toThrow('Unavailable')
})
it('reports no delay for an early start and preserves fractional execution minutes',()=>{
 const [event]=adaptBackendHistoryTasks([{...task,startedAt:'2026-10-25T09:29:00+08:00',finishedAt:'2026-10-25T09:30:30+08:00'}])
 expect(event.delayMinutes).toBe(0)
 expect(event.durationMinutes).toBe(1.5)
})
it('keeps history and robot IDs when the optional robot lookup fails',async()=>{
 vi.spyOn(taskApi,'getTaskRecords').mockResolvedValue([task])
 vi.spyOn(taskApi,'getRobots').mockRejectedValue(new Error('Robot lookup unavailable'))
 const source=await createHistorySource()
 expect(source.value.robotLookupFailed).toBe(true)
 expect(source.value.robots).toEqual([])
 expect(source.value.events[0]).toMatchObject({robotId:'robot-a',robotName:'C01',taskId:'T0001'})
})
it('keeps a task that failed before its scheduled time visible on its finish date',()=>{
 const [event]=adaptBackendHistoryTasks([{...task,status:'failed',scheduledAt:'2026-10-26T09:30:00+08:00',startedAt:null,finishedAt:'2026-10-25T09:00:00+08:00'}])
 expect(event.start).toBe(event.finishedAt)
 expect(event.durationMinutes).toBeNull()
 const date=new Date(event.finishedAt)
 const key=`${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`
 expect(eventsOnDay([event],key)).toHaveLength(1)
})

it('includes overdue pending tasks as delayed and excludes future pending tasks', () => {
 const pending={...task,status:'pending',startedAt:null,finishedAt:null,assignedRobot:null}
 const events=adaptBackendHistoryTasks([
  pending,
  {...pending,id:'future',scheduledAt:new Date(Date.now()+60000).toISOString()},
  {...pending,id:'assigned',status:'assigned'},
 ])
 expect(events).toHaveLength(1)
 expect(events[0]).toMatchObject({id:pending.id,status:'delayed',startedAt:null})
})
