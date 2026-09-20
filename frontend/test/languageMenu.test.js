import { mount } from '@vue/test-utils'
import { afterEach,expect,it } from 'vitest'
import { createMemoryHistory,createRouter } from 'vue-router'
import AppShellView from '@/views/AppShellView.vue'
import { setLocale } from '@/i18n/index.js'

afterEach(()=>setLocale('zh-TW'))
it('changes navbar and user menu labels without reloading and keeps the chosen locale',async()=>{
 const router=createRouter({history:createMemoryHistory(),routes:[{path:'/',name:'overview',component:{template:'<div />'}},{path:'/login',name:'login',component:{template:'<div />'}}]})
 await router.push('/');await router.isReady()
 const wrapper=mount(AppShellView,{global:{plugins:[router],stubs:{ClinicOverviewView:true,OverviewSearch:true}}})
 await wrapper.get('.user-menu-trigger').trigger('click')
 await wrapper.findAll('.user-menu button').find(button=>button.text().startsWith('語言')).trigger('click')
 await wrapper.findAll('.language-options button')[1].trigger('click')
 expect(wrapper.findAll('.overview-nav__link')[2].text()).toBe('Schedule History')
 expect(localStorage.getItem('hospital-rmf-locale')).toBe('en')
 await wrapper.get('.user-menu-trigger').trigger('click')
 expect(wrapper.get('.user-menu').text()).toContain('Edit profile')
 wrapper.unmount()
})
