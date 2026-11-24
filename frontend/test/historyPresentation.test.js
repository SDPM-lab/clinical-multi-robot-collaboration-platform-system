import { expect,it } from 'vitest'
import { getHistoryTaskColor,historyStatusColors,historyTaskStyle,summarizeHistory,taskColorMap } from '@/data/historyPresentation.js'
import { adaptHistoryTasks, filterHistory } from '@/data/scheduleHistory.js'
import { createRichDemoHistory } from '@/data/historyDemoData.js'
import { TASK_TYPE_BY_LABEL } from '@/config/taskTypes.js'
const events=[{title:'藥品配送',priority:'high',status:'completed',start:'2026-09-12T09:00:00',end:'2026-09-12T10:00:00'},{title:'檢體運送',priority:'normal',status:'cancelled',start:'2026-09-12T10:00:00',end:'2026-09-12T10:30:00'},{title:'清潔用品補充',status:'failed',start:'2026-09-12T12:00:00',end:'2026-09-12T12:30:00'}]
it('keeps history status colors centralized and fixed by semantic category',()=>{
 expect(historyStatusColors).toEqual({all:'var(--theme-primary)',completed:'#679A7B',cancelled:'#6489C7',failed:'#C47C70',delayed:'#A87434'})
 expect(new Set(Object.values(historyStatusColors)).size).toBe(5)
})
it('computes counts from task status only',()=>{
 expect(summarizeHistory(events)).toEqual({total:3,completed:1,cancelled:1,failed:1,delayed:0})
 expect(summarizeHistory(filterHistory(events,{title:['檢體運送']}))).toEqual({total:1,completed:0,cancelled:1,failed:0,delayed:0})
 expect(summarizeHistory([])).toEqual({total:0,completed:0,cancelled:0,failed:0,delayed:0})
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
it('adapts RobotTask fields and enum values for the history list',()=>{
 const tasks=[{id:'a1',taskType:'medication_delivery',source:'Pharmacy',destination:'Nurse Reception',priority:'emergency',status:'completed',assignedRobot:'R01',start:'2026-10-19T09:00:00',end:'2026-10-19T09:12:00',note:'Keep refrigerated',createdAt:'2026-10-18T08:00:00Z',requiredCapabilities:['Navigation','medication_delivery']}]
 expect(adaptHistoryTasks(tasks,[{id:'R01',name:'Robot 01'}])).toMatchObject([{taskId:'a1',title:'藥品配送',taskType:'medication_delivery',robotId:'R01',startLocation:'Pharmacy',endLocation:'Nurse Reception',priority:'urgent',status:'completed',requiredCapabilities:['Navigation','medication_delivery'],note:'Keep refrigerated',createdAt:'2026-10-18T08:00:00Z'}])
})
it('uses the four RobotTask types in demo schedule history',()=>{
 const events=createRichDemoHistory('2026-10-19')
 expect(new Set(events.map(event=>event.taskType))).toEqual(new Set(Object.values(TASK_TYPE_BY_LABEL)))
 expect(events.every(event=>event.requiredCapabilities.length>0)).toBe(true)
})
