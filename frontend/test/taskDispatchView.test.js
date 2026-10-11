import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import TaskDispatchView from '@/views/TaskDispatchView.vue'
import TaskForm from '@/components/dispatch/TaskForm.vue'
import DispatchMapScene from '@/components/dispatch/DispatchMapScene.vue'
import TaskScheduleSidebar from '@/components/dispatch/TaskScheduleSidebar.vue'
import { demoFleetStore } from '@/stores/demoFleetStore.js'
import { setLocale } from '@/i18n/index.js'
const graph=JSON.parse(readFileSync(resolve('public/generated/rmf-navigation.json'),'utf8'))
const floorplan=JSON.parse(readFileSync(resolve('public/generated/hospital-floorplan.json'),'utf8'))
let wrapper
beforeEach(()=>{
  vi.stubGlobal('ResizeObserver',class{observe(){} disconnect(){}})
  vi.stubGlobal('fetch',vi.fn(async url=>({ok:true,json:async()=>String(url).includes('hospital-floorplan')?floorplan:graph})))
})
afterEach(()=>{wrapper?.unmount();setLocale('zh-TW');vi.restoreAllMocks();vi.unstubAllGlobals()})
describe('task dispatch workspace',()=>{
  it('shows creation by default and switches the shared left panel to schedule',async()=>{
    wrapper=mount(TaskDispatchView, { global: { stubs: { DispatchMapScene: true } } });await flushPromises()
    expect(wrapper.get('#dispatch-create-tab').attributes('aria-selected')).toBe('true')
    expect(wrapper.get('#dispatch-schedule-panel').attributes('style')).toContain('display: none')
    await wrapper.get('#dispatch-schedule-tab').trigger('click')
    expect(wrapper.get('#dispatch-schedule-tab').attributes('aria-selected')).toBe('true')
    expect(wrapper.get('#dispatch-create-panel').attributes('style')).toContain('display: none')
    expect(wrapper.get('.schedule-sidebar').text()).toContain('藥品配送')
    wrapper.getComponent(DispatchMapScene).vm.$emit('select-location','Laboratory');await flushPromises()
    expect(wrapper.get('#dispatch-create-tab').attributes('aria-selected')).toBe('true')
    expect(wrapper.getComponent(TaskForm).props('origin')).toBe('Laboratory')
  })
  it('shows concurrent robots as separate compact schedule entries',()=>{
    const schedule=mount(TaskScheduleSidebar,{props:{date:'2026-08-31',robots:[{id:'R01',name:'Robot 01'},{id:'R02',name:'Robot 02'},{id:'R03',name:'Robot 03'}],tasks:[
      {id:'A',robotId:'R01',startTime:'09:30:00',endTime:'09:42:00',title:'藥品配送',origin:'藥局',destination:'護理站',status:'executing'},
      {id:'B',robotId:'R02',startTime:'09:30:00',endTime:'09:50:00',title:'檢體運送',origin:'診間',destination:'檢驗室',status:'executing'},
      {id:'C',robotId:'R03',startTime:'09:30:00',endTime:'09:45:00',title:'物資配送',origin:'倉庫',destination:'病房',status:'executing'},
    ]}})
    expect(schedule.findAll('.schedule-item')).toHaveLength(3)
    expect(schedule.findAll('.schedule-slot')).toHaveLength(1)
    expect(schedule.find('.schedule-time strong').text()).toBe('09:30')
    expect(schedule.findAll('.schedule-card-top').map((card)=>card.text())).toEqual(['A · R01','B · R02','C · R03'])
    expect(schedule.find('.schedule-slot').classes()).toContain('is-concurrent')
    expect(schedule.findAll('.schedule-item').map((item)=>item.attributes('title'))).toEqual([
      'Robot 01 · 藥品配送 · 藥局 → 護理站 · 09:30–09:42',
      'Robot 02 · 檢體運送 · 診間 → 檢驗室 · 09:30–09:50',
      'Robot 03 · 物資配送 · 倉庫 → 病房 · 09:30–09:45',
    ])
    expect(schedule.find('.schedule-status').exists()).toBe(false)
    expect(schedule.find('.schedule-progress').exists()).toBe(false)
    schedule.unmount()
  })
  it('links form endpoints, map selection and robot status while retaining all payload fields',async()=>{
    wrapper=mount(TaskDispatchView, { global: { stubs: { DispatchMapScene: true } } });await flushPromises()
    const form=wrapper.getComponent(TaskForm),map=wrapper.getComponent(DispatchMapScene)
    expect(map.props('routeConfirmed')).toBe(false)
    map.vm.$emit('select-location', 'Laboratory'); await flushPromises()
    expect(form.props('origin')).toBe('Laboratory')
    expect(map.props('routeConfirmed')).toBe(false)
    map.vm.$emit('select-location', 'Ward A'); await flushPromises()
    expect(form.props('destination')).toBe('Ward A')
    expect(map.props('routeConfirmed')).toBe(true)
    map.vm.$emit('select-location', 'Pharmacy'); await flushPromises()
    expect(form.props('origin')).toBe('Pharmacy')
    expect(map.props('routeConfirmed')).toBe(false)
    await form.findAll('.location-trigger')[0].trigger('click')
    await form.findAll('.location-options [role="option"]')[6].trigger('click')
    expect(form.findAll('.location-trigger')[0].text()).toBe('檢驗室')
    expect(map.props('routeConfirmed')).toBe(false)
    await form.findAll('.location-trigger')[1].trigger('click')
    await form.findAll('.location-options [role="option"]')[7].trigger('click')
    expect(map.props('destination')).toBe('Pantry')
    expect(map.props('routeConfirmed')).toBe(true)
    expect(form.find('[aria-label="清除任務表單"]').exists()).toBe(false)
    expect(form.text()).not.toContain('預計結束時間')
    expect(form.text()).not.toContain('預估時長')
    expect(form.text()).not.toContain('示範模式')
    const note=form.get('textarea[placeholder="輸入交接方式或注意事項"]')
    await note.setValue('交給值班護理師')
    const create=vi.spyOn(demoFleetStore,'createTask').mockReturnValue({ok:true})
    await form.get('form').trigger('submit')
    expect(create).toHaveBeenCalledWith(expect.objectContaining({origin:'Laboratory',destination:'Pantry',robotId:'R01',type:'藥品配送',title:'藥品配送',date:'2026-08-31',startTime:'09:30:00',durationSeconds:720,priority:'normal',notes:'交給值班護理師'}))
    expect(form.props('locations')).not.toContain('Charging Station B')
  })
  it('edits directly in the schedule and asks before deleting',async()=>{
    wrapper=mount(TaskDispatchView, { global: { stubs: { DispatchMapScene: true } } });await flushPromises()
    expect(wrapper.get('.schedule-sidebar').text()).toContain('藥品配送')
    await wrapper.get('.schedule-date-navigation button[aria-label="後一天"]').trigger('click')
    expect(wrapper.get('.schedule-sidebar').text()).toContain('目前沒有排定任務')
    await wrapper.get('.schedule-date-navigation button[aria-label="前一天"]').trigger('click')
    await wrapper.get('.schedule-edit').trigger('click')
    expect(wrapper.get('.schedule-edit').attributes('aria-pressed')).toBe('true')
    expect(wrapper.find('.schedule-editor').exists()).toBe(false)
    expect(wrapper.findAll('.schedule-delete')).toHaveLength(5)
    const move=vi.spyOn(demoFleetStore,'moveTask').mockReturnValue({ok:true})
    await wrapper.get('.schedule-inline-edit input').setValue('09:45')
    await wrapper.get('.schedule-inline-edit button').trigger('click')
    expect(move).toHaveBeenCalledWith('T001',35100)
    const remove=vi.spyOn(demoFleetStore,'deleteTask').mockReturnValue({ok:true})
    await wrapper.get('.schedule-delete').trigger('click')
    expect(wrapper.get('[role="alertdialog"]').text()).toContain('T001')
    await wrapper.get('.dispatch-confirm-actions button').trigger('click')
    expect(remove).not.toHaveBeenCalled()
    await wrapper.get('.schedule-delete').trigger('click')
    await wrapper.get('.dispatch-confirm-actions .is-danger').trigger('click')
    expect(remove).toHaveBeenCalledWith('T001')
    expect(wrapper.find('[role="alertdialog"]').exists()).toBe(false)
  })
  it('shows a localized delete confirmation and custom robot choices',async()=>{
    setLocale('en')
    wrapper=mount(TaskDispatchView, { global: { stubs: { DispatchMapScene: true } } });await flushPromises()
    await wrapper.get('.robot-trigger').trigger('click')
    expect(wrapper.findAll('.robot-options [role="option"]')).toHaveLength(3)
    expect(wrapper.get('.robot-options').text()).toContain('In progress')
    await wrapper.findAll('.robot-options [role="option"]')[1].trigger('click')
    expect(wrapper.getComponent(TaskForm).props('robotId')).toBe('R02')
    await wrapper.get('.schedule-edit').trigger('click')
    await wrapper.get('.schedule-delete').trigger('click')
    expect(wrapper.get('[role="alertdialog"]').text()).toContain('Delete T001')
    expect(wrapper.get('.dispatch-confirm-actions .is-danger').text()).toBe('Delete')
  })
  it('uses styled task type choices and submits a stable AM/PM time',async()=>{
    wrapper=mount(TaskDispatchView, { global: { stubs: { DispatchMapScene: true } } });await flushPromises()
    const form=wrapper.getComponent(TaskForm)
    await form.get('.task-type-trigger').trigger('click')
    expect(form.findAll('.task-type-options [role="option"]')).toHaveLength(7)
    await form.findAll('.task-type-options [role="option"]')[1].trigger('click')
    expect(form.get('.task-type-trigger').text()).toBe('檢體運送')
    await form.get('#dispatch-start-time').setValue('02:45 PM')
    const create=vi.spyOn(demoFleetStore,'createTask').mockReturnValue({ok:true})
    await form.get('form').trigger('submit')
    expect(create).toHaveBeenCalledWith(expect.objectContaining({type:'檢體運送',startTime:'14:45:00',durationSeconds:720}))
  })
  it('returns the schedule to the current local date',async()=>{
    wrapper=mount(TaskDispatchView, { global: { stubs: { DispatchMapScene: true } } });await flushPromises()
    const now=new Date(), today=`${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`
    await wrapper.get('.schedule-today').trigger('click')
    expect(wrapper.getComponent(TaskScheduleSidebar).props('date')).toBe(today)
  })
  it('updates the form and deletion dialog when the language changes without reloading',async()=>{
    wrapper=mount(TaskDispatchView, { global: { stubs: { DispatchMapScene: true } } });await flushPromises()
    await wrapper.get('.schedule-edit').trigger('click')
    await wrapper.get('.schedule-delete').trigger('click')
    expect(wrapper.get('[role="alertdialog"]').text()).toContain('刪除這項任務')
    setLocale('en');await flushPromises()
    expect(wrapper.get('.task-panel').text()).toContain('Create task')
    expect(wrapper.get('[role="alertdialog"]').text()).toContain('Delete this task?')
    expect(wrapper.get('[role="alertdialog"]').text()).toContain('Medication delivery')
  })
  it('displays task validation errors and keeps the form available',async()=>{
    wrapper=mount(TaskDispatchView, { global: { stubs: { DispatchMapScene: true } } });await flushPromises()
    vi.spyOn(demoFleetStore,'createTask').mockReturnValue({ok:false,reason:'與既有任務時間重疊。'})
    await wrapper.get('form').trigger('submit')
    expect(wrapper.get('.dispatch-toast').text()).toContain('時間重疊')
    expect(wrapper.get('.create-button').exists()).toBe(true)
  })
})
