import { afterEach,expect,it,vi } from 'vitest'
import { nextTick } from 'vue'
import { installGlobalTranslation,setLocale,t } from '@/i18n/index.js'

afterEach(()=>{setLocale('zh-TW');document.body.innerHTML=''})
it('persists locale and translates known literal UI copy without changing identifiers',async()=>{
 const root=document.createElement('div')
 root.innerHTML='<h2>今日完成率</h2><input placeholder="搜尋任務、機器人或區域"><span>Robot R01</span><button>全部 3</button>'
 document.body.append(root)
 const dispose=installGlobalTranslation(root)
 setLocale('en')
 await nextTick()
 expect(root.querySelector('h2').textContent).toBe("Today's completion rate")
 expect(root.querySelector('input').placeholder).toBe('Search tasks, robots or areas')
 expect(root.querySelector('span').textContent).toBe('Robot R01')
 expect(root.querySelector('button').textContent).toBe('All 3')
 expect(t('nav.history')).toBe('Schedule History')
 expect(localStorage.getItem('hospital-rmf-locale')).toBe('en')
 setLocale('zh-TW')
 await nextTick()
 expect(root.querySelector('h2').textContent).toBe('今日完成率')
 dispose()
})
it('restores the saved English locale when the i18n module initializes again',async()=>{
 setLocale('en')
 vi.resetModules()
 const fresh=await import('@/i18n/index.js')
 expect(fresh.locale.value).toBe('en')
 expect(fresh.t('history.title')).toBe('Schedule History')
 fresh.setLocale('zh-TW')
})
