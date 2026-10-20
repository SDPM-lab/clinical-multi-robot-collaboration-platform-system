import { mount,flushPromises } from '@vue/test-utils'
import { computed } from 'vue'
import { expect,it,vi,beforeEach,afterEach } from 'vitest'
import SharedLoading from '@/components/SharedLoading.vue'
import ScheduleHistoryView from '@/views/ScheduleHistoryView.vue'
const control=vi.hoisted(()=>({error:false,events:[]}))
vi.mock('@/data/scheduleHistorySource.js',()=>({createHistorySource:()=>{if(control.error)throw new Error('Failed');return computed(()=>({events:control.events,demo:false,error:''}))}}))
beforeEach(()=>{control.error=false;control.events=[];vi.stubGlobal('ResizeObserver',class{observe(){} disconnect(){}})})
afterEach(()=>vi.unstubAllGlobals())
const ready=async()=>{await vi.dynamicImportSettled();await flushPromises()}
it('uses the shared loader, then shows an honest empty state without a timer',async()=>{
 const wrapper=mount(ScheduleHistoryView)
 expect(wrapper.findComponent(SharedLoading).props('loading')).toBe(true)
 await ready()
 expect(wrapper.get('.list-content').attributes('aria-busy')).toBe('false')
 expect(wrapper.find('.scene-spinner').exists()).toBe(false)
 expect(wrapper.find('.history-empty').exists()).toBe(true)
 expect(wrapper.find('.history-empty button').exists()).toBe(false)
 expect(wrapper.get('.task-record-empty').text()).toBe('沒有符合條件的任務')
 expect(wrapper.findAll('.history-metric')).toHaveLength(4)
 wrapper.unmount()
})
it('shows errors and retries initialization using the same loader',async()=>{
 control.error=true
 const wrapper=mount(ScheduleHistoryView);await ready()
 expect(wrapper.get('.list-content').attributes('aria-busy')).toBe('false')
 expect(wrapper.get('[role=alert]').text()).toContain('請重試')
 control.error=false
 await wrapper.get('[role=alert] button').trigger('click');await ready()
 expect(wrapper.find('.history-empty').exists()).toBe(true)
 wrapper.unmount()
})
it('opens the latest recorded day when there are no tasks today',async()=>{
 control.events=[{id:'historic-1',taskId:'H999001',title:'藥品配送',robotId:'R01',robotName:'Robot 01',start:'2026-08-31T09:00:00',end:'2026-08-31T09:35:00',startLocation:'Pharmacy',endLocation:'Nurse Reception',priority:'high',status:'completed'}]
 const wrapper=mount(ScheduleHistoryView);await ready()
 expect(wrapper.get('.history-date-picker').text()).toBe('2026/08/31')
 expect(wrapper.get('.detail-header').text()).toContain('H999001')
 wrapper.unmount()
})
