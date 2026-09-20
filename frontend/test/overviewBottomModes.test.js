import { mount } from '@vue/test-utils'
import { expect,it } from 'vitest'
import ClinicOverviewView from '@/views/ClinicOverviewView.vue'
import { overviewDemoData } from '@/data/overviewDemoData.js'
it('switches from building charts to scoped floor robots and back',async()=>{
 const wrapper=mount(ClinicOverviewView,{props:{data:overviewDemoData},global:{stubs:{ClinicOverviewScene:true}}})
 expect(wrapper.findAll('.floor-chart')).toHaveLength(3)
 expect(wrapper.find('.average-line').exists()).toBe(false)
 expect(wrapper.text()).not.toContain('平均電量')
 expect(wrapper.get('.bottom-status-panel').attributes('data-mode')).toBe('building-trend')
 expect(wrapper.find('.floor-realtime-panel').exists()).toBe(false)
 await wrapper.findAll('.floor-label')[2].trigger('click')
 expect(wrapper.find('.floor-chart').exists()).toBe(false)
 expect(wrapper.get('.bottom-status-panel').attributes('data-mode')).toBe('floor-realtime')
 expect(wrapper.findAll('.robot-trend-column')).toHaveLength(3)
 expect(wrapper.findAll('.battery-segments span')).toHaveLength(30)
 expect(wrapper.findAll('.robot-battery-trend')).toHaveLength(3)
 expect(wrapper.find('img').exists()).toBe(false)
 expect(wrapper.findAll('.battery-range-tabs').at(0).text()).toBe('DayWeeklyMonthly')
 await wrapper.findAll('.floor-label')[1].trigger('click')
 expect(wrapper.get('.floor-realtime-panel').attributes('aria-label')).toContain('Floor 2')
 await wrapper.get('.all-floor').trigger('click')
 expect(wrapper.findAll('.floor-chart')).toHaveLength(3)
 wrapper.unmount()
})

it('updates only scoped values while preserving mounted robot rows',async()=>{
 const data={...overviewDemoData,robots:overviewDemoData.robots.map(robot=>({...robot}))}
 const wrapper=mount(ClinicOverviewView,{props:{data},global:{stubs:{ClinicOverviewScene:true}}})
 await wrapper.findAll('.floor-label')[2].trigger('click')
 const panel=wrapper.get('.bottom-status-panel').element
 const rows=wrapper.findAll('.robot-trend-column').map(row=>row.element)
 await wrapper.setProps({data:{...data,robots:data.robots.map(robot=>robot.id==='R01'?{...robot,battery:79}:robot)}})
 expect(wrapper.get('.bottom-status-panel').element).toBe(panel)
 expect(wrapper.findAll('.robot-trend-column').map(row=>row.element)).toEqual(rows)
 expect(wrapper.findAll('.battery-segments')).toHaveLength(3)
 wrapper.unmount()
})

it('keeps battery bar groups clear of the y-axis and each other',()=>{
 const wrapper=mount(ClinicOverviewView,{props:{data:overviewDemoData},global:{stubs:{ClinicOverviewScene:true}}})
 const chart=wrapper.findAll('.floor-chart')[0]
 const bars=chart.findAll('.robot-bar').map(bar=>({x:Number(bar.attributes('x')),width:Number(bar.attributes('width'))}))
 const groups=Array.from({length:5},(_,index)=>bars.slice(index*3,index*3+3))
 expect(Math.min(...groups[0].map(bar=>bar.x))).toBeGreaterThan(34)
 for(let index=0;index<groups.length-1;index+=1){
  const right=Math.max(...groups[index].map(bar=>bar.x+bar.width))
  const left=Math.min(...groups[index+1].map(bar=>bar.x))
  expect(left-right).toBeGreaterThan(8)
 }
 expect(chart.findAll('.chart-axes text').map(label=>label.attributes('x'))).toEqual(['30','30','30'])
 wrapper.unmount()
})
