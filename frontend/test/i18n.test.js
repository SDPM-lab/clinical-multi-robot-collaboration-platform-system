import { afterEach,expect,it,vi } from 'vitest'
import { nextTick } from 'vue'
import { installGlobalTranslation,setLocale,t,translateLocation } from '@/i18n/index.js'
import en from '@/i18n/locales/en.js'
import zhTW from '@/i18n/locales/zh-TW.js'

const localeKeys = (messages, prefix = '') => Object.entries(messages)
 .filter(([key]) => key !== 'legacy')
 .flatMap(([key, value]) => {
  const path = prefix ? `${prefix}.${key}` : key
  return value && typeof value === 'object' ? localeKeys(value, path) : [path]
 })
 .sort()

afterEach(()=>{setLocale('zh-TW');document.body.innerHTML=''})
it('keeps keyed English and Chinese translations complete across the app',()=>{
 expect(localeKeys(zhTW)).toEqual(localeKeys(en))
})
it('translates exact location names including apostrophes',()=>{
 setLocale('zh-TW')
 expect(translateLocation("Women's Restroom")).toBe('女廁')
 setLocale('en')
 expect(translateLocation("Women's Restroom")).toBe("Women's Restroom")
})
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
