import { describe, expect, it } from 'vitest'
import { dashboardSnapshot } from '@/data/dashboardSnapshot.js'

describe('dashboard backend alignment', () => {
  it('uses the same task fields for calendar and the running route', () => {
    const today = new Date(2026, 10, 9)
    const robots = Array.from({length:7},(_,index)=>({ id:index===0?'robot-a':index===1?'robot-b':`robot-hospital_robot_${index+1}`, levelName:'L1', status:'離線', hasTelemetry:false }))
    const record = { id:'uuid-1', taskCode:'T0001', taskType:'medication_delivery', source:'ward_a_1', destination:'reception_back', scheduledAt:new Date(2026,10,9,10).toISOString(), assignedRobot:'robot-a', status:'running' }
    const graph = { namedWaypoints:[{id:'v1',name:'ward_a_1'},{id:'v3',name:'reception_back'}], vertices:[{id:'v1',name:'ward_a_1'},{id:'v2',name:'left_junction'},{id:'v3',name:'reception_back'}], lanes:[{from:'v1',to:'v2'},{from:'v2',to:'v3'}] }
    const result = dashboardSnapshot({ robots }, [record], graph, today)
    expect(result.robots).toHaveLength(7)
    expect(Object.keys(result.progressByRobot)).toHaveLength(7)
    expect(result.calendarDates.find(day=>day.today).items[0]).toMatchObject({assignee:'C01',route:'Ward A → Nurse Reception'})
    expect(result.progressByRobot['robot-a'].steps.map(step=>step.location)).toEqual(['—','Ward A','Nurse Reception'])
    expect(result.progressByRobot['robot-a'].steps.map(step=>step.role)).toEqual(['currentLocation','source','destination'])
    expect(result.completion).toMatchObject({completed:0,total:1,percentage:0})
  })
})
