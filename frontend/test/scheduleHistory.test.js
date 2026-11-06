import { describe,it,expect } from 'vitest'
import { historyRange,monthDays,filterHistory,layoutDayEvents,adaptHistoryTasks } from '@/data/scheduleHistory.js'
const event={id:'a',taskId:'T1',title:'藥品配送',robotId:'R01',robotName:'Robot 01',start:'2026-09-11T09:00:00',end:'2026-09-11T10:00:00',startLocation:'Pharmacy',endLocation:'Clinic',priority:'high',status:'completed'}
describe('readonly schedule history',()=>{
 it('uses local dates for week/month ranges and a complete mini calendar',()=>{
  expect(historyRange('2026-09-11','weekly')).toEqual(['2026-09-07','2026-09-14'])
  expect(historyRange('2026-12-31','monthly')).toEqual(['2026-12-01','2027-01-01'])
  expect(monthDays('2026-09-11')).toHaveLength(42)
 })
 it('combines multi-select filters and searches both endpoint locations',()=>{
  expect(filterHistory([event],{priority:['high','low'],location:['Clinic']},'robot 01')).toHaveLength(1)
  expect(filterHistory([event],{status:['failed']})).toHaveLength(0)
 })
 it('places overlapping records in separate lanes and clips midnight crossings',()=>{
  const rows=layoutDayEvents([event,{...event,id:'b',start:'2026-09-11T09:30:00',end:'2026-09-11T11:00:00'}],'2026-09-11')
  expect(rows.map(row=>row.lane)).toEqual([0,1]);expect(rows[0].lanes).toBe(2)
  const night=layoutDayEvents([{...event,start:'2026-09-10T23:30:00',end:'2026-09-11T00:30:00'}],'2026-09-11')[0]
  expect(night.top).toBe(0);expect(night.height).toBe(38)
 })
 it('shows dated planned tasks as waiting without inventing dates for undated tasks',()=>{
  expect(adaptHistoryTasks([{id:'T1',status:'scheduled',date:'2026-09-11',startTime:'09:00',endTime:'10:00'}],[])).toMatchObject([{taskId:'T1',status:'waiting',start:'2026-09-11T09:00',end:'2026-09-11T10:00'}])
  expect(adaptHistoryTasks([{id:'T1',status:'executing',startTime:'09:00',endTime:'10:00'}],[])).toEqual([])
 })
})
