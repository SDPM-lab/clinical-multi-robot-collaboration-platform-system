import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { afterEach,expect,it,vi } from 'vitest'
import ClinicOverviewView from '@/views/ClinicOverviewView.vue'
import RobotFleetView from '@/views/RobotFleetView.vue'
import TaskDispatchView from '@/views/TaskDispatchView.vue'
import { overviewDemoData } from '@/data/overviewDemoData.js'
import { installGlobalTranslation,setLocale } from '@/i18n/index.js'

afterEach(()=>{setLocale('zh-TW');vi.unstubAllGlobals()})
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
 for(const tab of wrapper.findAll('.robot-inspector-tabs button')){await tab.trigger('click');await nextTick();await new Promise(resolve=>setTimeout(resolve,10));expect(untranslatedText(wrapper.element)).toEqual([])}
 dispose();wrapper.unmount()
})
it('translates visible dispatch interface copy while preserving Robot and task IDs',async()=>{
 vi.stubGlobal('ResizeObserver',class{observe(){} disconnect(){}})
 const wrapper=mount(TaskDispatchView,{global:{stubs:{HospitalMiniMap:true}}})
 const dispose=await switchPage(wrapper)
 expect(untranslatedText(wrapper.element)).toEqual([])
 expect(wrapper.text()).toContain('T001')
 expect(wrapper.text()).toContain('Robot 01')
 const taskOption=wrapper.get('.task-panel select option').element
 expect(taskOption.textContent).toBe('Medication delivery')
 expect(taskOption.value).toBe('藥品配送')
 dispose();wrapper.unmount()
})
