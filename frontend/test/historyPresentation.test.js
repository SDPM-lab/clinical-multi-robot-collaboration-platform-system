import { expect,it } from 'vitest'
import { getHistoryTaskColor,historyStatusColors,historyTaskStyle,summarizeHistory,taskColorMap } from '@/data/historyPresentation.js'
import { filterHistory } from '@/data/scheduleHistory.js'
const events=[{title:'藥品配送',priority:'high',status:'completed',start:'2026-09-12T09:00:00',end:'2026-09-12T10:00:00'},{title:'檢體運送',priority:'normal',status:'cancelled',start:'2026-09-12T10:00:00',end:'2026-09-12T10:30:00'},{title:'清潔用品補充',status:'failed',start:'2026-09-12T12:00:00',end:'2026-09-12T12:30:00'}]
it('keeps the five history summary colors centralized and fixed by semantic category',()=>{
 expect(historyStatusColors).toEqual({all:'var(--theme-primary)',completed:'#2FA58F',cancelled:'#4F7DF3',overdue:'#E0B52E',failed:'#E45D63'})
 expect(new Set(Object.values(historyStatusColors)).size).toBe(5)
})
it('computes the five requested summary counts',()=>{
 expect(summarizeHistory(events)).toEqual({total:3,completed:1,cancelled:1,overdue:0,failed:1})
 expect(summarizeHistory(filterHistory(events,{title:['檢體運送']}))).toEqual({total:1,completed:0,cancelled:1,overdue:0,failed:0})
 expect(summarizeHistory([])).toEqual({total:0,completed:0,cancelled:0,overdue:0,failed:0})
})
it('derives overdue tasks from unfinished records whose expected end has passed',()=>{
 const records=[
  {status:'running',end:'2026-09-16T09:00:00'},
  {status:'waiting',end:'2026-09-16T20:00:00'},
  {status:'completed',end:'2026-09-16T08:00:00'},
 ]
 expect(summarizeHistory(records,Date.parse('2026-09-16T12:00:00')).overdue).toBe(1)
})
it('maps task names deterministically regardless of priority and has a neutral fallback',()=>{
 expect(historyTaskStyle(events[0].title)).toEqual(historyTaskStyle({...events[0],priority:'low'}.title))
 expect(getHistoryTaskColor('藥品配送')).not.toEqual(getHistoryTaskColor('檢體運送'))
 expect(getHistoryTaskColor('充電')).toEqual(getHistoryTaskColor('返回充電站'))
 expect(getHistoryTaskColor('新的任務')).toEqual(getHistoryTaskColor('另一個任務'))
})
it('assigns six requested task names six stable and distinct colors',()=>{
 const names=['藥品配送','檢體運送','病房物資補充','門診文件配送','醫療廢棄物運送','清潔用品補充']
 expect(names.every(name=>taskColorMap[name])).toBe(true)
 expect(new Set(names.map(name=>getHistoryTaskColor(name).ink)).size).toBe(6)
})
