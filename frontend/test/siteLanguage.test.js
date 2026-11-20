import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { afterEach,expect,it,vi } from 'vitest'
import ClinicOverviewView from '@/views/ClinicOverviewView.vue'
import RobotFleetView from '@/views/RobotFleetView.vue'
import TaskDispatchView from '@/views/TaskDispatchView.vue'
import { overviewDemoData } from '@/data/overviewDemoData.js'
import { installGlobalTranslation,setLocale } from '@/i18n/index.js'
import { taskApi } from '@/services/taskApi.js'
import { demoFleetStore } from '@/stores/demoFleetStore.js'

afterEach(()=>{setLocale('zh-TW');vi.restoreAllMocks();vi.unstubAllGlobals()})
const untranslatedText=root=>{const nodes=[];const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);while(walker.nextNode()){const value=walker.currentNode.textContent.trim();if(/[一-龥]/u.test(value))nodes.push(value)}return [...new Set(nodes)]}
const switchPage=async wrapper=>{const dispose=installGlobalTranslation(wrapper.element);setLocale('en');await nextTick();await new Promise(resolve=>setTimeout(resolve,20));return dispose}

it('translates visible overview interface copy',async()=>{
 const wrapper=mount(ClinicOverviewView,{props:{data:overviewDemoData,theme:'light'},global:{stubs:{ClinicOverviewScene:true}}})
 const dispose=await switchPage(wrapper)
 expect(untranslatedText(wrapper.element)).toEqual([])
 dispose();wrapper.unmount()
})
it('translates visible robot interface copy in every inspector tab',async()=>{
 const wrapper=mount(RobotFleetView,{global:{stubs:{RobotViewport:true,ChargingRoutePlane:true}}})
 const dispose=await switchPage(wrapper)
 for(const tab of wrapper.findAll('.robot-accordion summary')){await tab.trigger('click');await nextTick();await new Promise(resolve=>setTimeout(resolve,10));expect(untranslatedText(wrapper.element)).toEqual([])}
 dispose();wrapper.unmount()
})
it('translates visible dispatch interface copy while preserving Robot and task IDs',async()=>{
 vi.stubGlobal('ResizeObserver',class{observe(){} disconnect(){}})
 const now=new Date()
 const date=`${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`
 vi.spyOn(taskApi,'getTasks').mockResolvedValue(demoFleetStore.tasks.value.map(task=>({...task,date})))
 vi.spyOn(taskApi,'getRobots').mockResolvedValue([...demoFleetStore.robots.value])
 const wrapper=mount(TaskDispatchView,{global:{stubs:{DispatchMapScene:true}}})
 const dispose=await switchPage(wrapper)
 expect(untranslatedText(wrapper.element)).toEqual([])
 expect(wrapper.text()).toContain('T001')
 await wrapper.get('.task-type-trigger').trigger('click')
 const taskOption=wrapper.get('.task-type-options [role="option"]')
 expect(taskOption.text()).toBe('Medication delivery')
 expect(taskOption.attributes('aria-selected')).toBe('true')
 dispose();wrapper.unmount()
})
