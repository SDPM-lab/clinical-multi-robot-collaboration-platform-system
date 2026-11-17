import {readFileSync} from 'node:fs'
import {expect,it} from 'vitest'
import {priorityOrder} from '@/data/demoActiveRoutes.js'
import {setLocale,t} from '@/i18n/index.js'
it('uses the backend priority enum values and the shared emergency label',()=>{
 const source=readFileSync('../backend/Server/Models/TaskPriority.cs','utf8')
 const values=[...source.matchAll(/\b(Low|Normal|High|Emergency)\s*=/g)].map(match=>match[1].toLowerCase())
 expect(Object.keys(priorityOrder).sort()).toEqual(values.sort())
 setLocale('en')
 try {expect(t('priority.emergency')).toBe('Emergency');expect(t('liveMap.roomLabels')).toBe('All room labels')}
 finally {setLocale('zh-TW')}
})
