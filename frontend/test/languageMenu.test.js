import { mount } from '@vue/test-utils'
import { afterEach,expect,it } from 'vitest'
import { createMemoryHistory,createRouter } from 'vue-router'
import AppShellView from '@/views/AppShellView.vue'
import { setLocale } from '@/i18n/index.js'

afterEach(()=>{
 setLocale('zh-TW')
 localStorage.removeItem('hospital-rmf-font-size')
 document.documentElement.dataset.uiFontSize='small'
})
it('changes navbar and user menu labels without reloading and keeps the chosen locale',async()=>{
 const router=createRouter({history:createMemoryHistory(),routes:[{path:'/',name:'overview',component:{template:'<div />'}},{path:'/login',name:'login',component:{template:'<div />'}}]})
 await router.push('/');await router.isReady()
 const wrapper=mount(AppShellView,{global:{plugins:[router],stubs:{ClinicOverviewView:true}}})
 expect(wrapper.find('.overview-search').exists()).toBe(false)
 await wrapper.get('.user-menu-trigger').trigger('click')
 await wrapper.findAll('.user-menu button').find(button=>button.text().startsWith('語言')).trigger('click')
 await wrapper.findAll('.language-options button')[1].trigger('click')
 expect(wrapper.findAll('.overview-nav__link')[2].text()).toBe('Schedule History')
 expect(localStorage.getItem('hospital-rmf-locale')).toBe('en')
 await wrapper.get('.user-menu-trigger').trigger('click')
 expect(wrapper.get('.user-menu').text()).toContain('Edit profile')
 expect(wrapper.get('.font-size-setting').attributes('aria-label')).toBe('Font size')
 expect(wrapper.findAll('.font-size-options button').map(button=>button.text())).toEqual(['Small','Medium','Large'])
 expect(wrapper.findAll('.font-size-options button')[0].attributes('aria-pressed')).toBe('true')
 await wrapper.findAll('.font-size-options button')[1].trigger('click')
 expect(document.documentElement.dataset.uiFontSize).toBe('medium')
 expect(localStorage.getItem('hospital-rmf-font-size')).toBe('medium')
 expect(wrapper.findAll('.font-size-options button')[1].attributes('aria-pressed')).toBe('true')
 await wrapper.findAll('.font-size-options button')[2].trigger('click')
 expect(document.documentElement.dataset.uiFontSize).toBe('large')
 expect(localStorage.getItem('hospital-rmf-font-size')).toBe('large')
 expect(wrapper.findAll('.font-size-options button')[2].attributes('aria-pressed')).toBe('true')
 wrapper.unmount()
})
