import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import HospitalMiniMap from '@/components/dispatch/HospitalMiniMap.vue'
import { rmfToMapPoint } from '@/components/dispatch/dispatchMapGeometry.js'
const graph = JSON.parse(readFileSync(resolve('public/generated/rmf-navigation.json'), 'utf8'))
const floorplan = JSON.parse(readFileSync(resolve('public/generated/hospital-floorplan.json'), 'utf8'))
let wrappers = []
const robots = [{id:'R01',currentLocation:'Nurse Reception',battery:82}]
const pointer = async (element, type, x, y) => {
  const event = new Event(type, {bubbles:true})
  Object.assign(event,{clientX:x,clientY:y,pointerId:1,button:0})
  element.dispatchEvent(event)
  await flushPromises()
}
const create = async (props = {}, navigation = graph) => {
  vi.stubGlobal('fetch',vi.fn(async (url) => ({ok:true,json:async () => String(url).includes('hospital-floorplan') ? floorplan : navigation})))
  const wrapper = mount(HospitalMiniMap,{props:{robots,source:'Pharmacy',destination:'Nurse Reception',...props}})
  wrappers.push(wrapper); await flushPromises(); return wrapper
}
beforeEach(() => vi.stubGlobal('ResizeObserver',class {observe(){} disconnect(){}}))
afterEach(() => { wrappers.forEach(w=>w.unmount()); wrappers=[]; vi.unstubAllGlobals() })
describe('dispatch SVG map', () => {
  it('renders only verified rooms, with current names and graph-connected routes', async () => {
    const w = await create()
    expect(w.findAll('.room-region')).toHaveLength(14)
    expect(w.get('[data-room="consultation-3"]').text()).toContain('診間 3')
    expect(w.find('[data-room="pharmacy"]').exists()).toBe(false)
    const points = w.get('.estimate-route').attributes('points').split(' ')
    expect(points.length).toBeGreaterThan(2)
    const vertexIds = points.map((point) => graph.vertices.find((v)=>{const p=rmfToMapPoint(v);return `${p.x},${p.y}`===point}).id)
    vertexIds.slice(1).forEach((id,i)=>expect(graph.lanes.some(lane=>lane.from===vertexIds[i]&&lane.to===id)).toBe(true))
  })
  it('selects either endpoint using markers or explicit room mapping', async () => {
    const w = await create({selectionMode:'source',allowedLocations:['Laboratory','Nurse Reception']})
    await w.get('[data-waypoint="lab"]').trigger('keydown',{key:'Enter'})
    expect(w.emitted('select-source')[0]).toEqual(['Laboratory'])
    await w.setProps({selectionMode:'destination'})
    await w.get('[data-room="laboratory"]').trigger('keydown',{key:'Enter'})
    expect(w.emitted('select-destination')[0]).toEqual(['Laboratory'])
    await w.get('[data-waypoint="charging_station_2"]').trigger('keydown',{key:'Enter'})
    expect(w.emitted('select-destination')).toHaveLength(1)
  })
  it('requires choosing a station when a room has multiple permitted stations', async () => {
    const w = await create({allowedLocations:['Charging Station A','Charging Station B']})
    await w.get('[data-room="charging"]').trigger('keydown',{key:'Enter'})
    expect(w.emitted('select-destination')).toBeUndefined()
    expect(w.findAll('.destination-button')).toHaveLength(2)
    await w.findAll('.destination-button')[1].trigger('click')
    expect(w.emitted('select-destination')[0]).toEqual(['Charging Station B'])
  })
  it('pans in SVG units and suppresses selection after dragging from a marker', async () => {
    const w = await create()
    const svg = w.get('svg').element
    svg.getScreenCTM=()=>({inverse:()=>({})})
    svg.createSVGPoint=()=>({x:0,y:0,matrixTransform(){return {x:this.x/2,y:this.y/2}}})
    const before=w.get('.map-world').attributes('transform')
    await pointer(w.get('[data-waypoint="lab"] circle').element,'pointerdown',100,100)
    await pointer(svg,'pointermove',160,140)
    await pointer(svg,'pointerup',160,140)
    expect(w.emitted('select-destination')).toBeUndefined()
    const translation=(value)=>value.match(/translate\(([-.\d]+) ([-.\d]+)\)/).slice(1).map(Number)
    const a=translation(before),b=translation(w.get('.map-world').attributes('transform'))
    expect(b[0]-a[0]).toBeCloseTo(30);expect(b[1]-a[1]).toBeCloseTo(20)
    await pointer(w.get('[data-waypoint="lab"] circle').element,'pointerdown',100,100)
    await pointer(svg,'pointerup',100,100)
    expect(w.emitted('select-destination')[0]).toEqual(['Laboratory'])
  })
  it('updates robot positions and both endpoint highlights without remounting', async () => {
    const w=await create()
    const before=w.get('[data-robot="R01"]').attributes('transform')
    await w.setProps({robots:[{...robots[0],currentLocation:'Laboratory'}],source:'Laboratory',destination:'Ward A'})
    expect(w.get('[data-robot="R01"]').attributes('transform')).not.toBe(before)
    expect(w.get('[data-waypoint="lab"] .source').exists()).toBe(true)
    expect(w.get('[data-waypoint="ward_a_1"] .destination').exists()).toBe(true)
    await w.setProps({robots:[{...robots[0],rmfPosition:{x:10,y:-10,level:'L1'}}]})
    const point=rmfToMapPoint({x:10,y:-10})
    expect(w.get('[data-robot="R01"]').attributes('transform')).toBe(`translate(${point.x} ${point.y})`)
  })
  it('does not draw a straight-line fallback when no directed route exists', async () => {
    const w=await create({}, {...graph,lanes:[]})
    expect(w.find('.estimate-route').exists()).toBe(false)
    expect(w.text()).toContain('沒有可用路線')
  })
  it('retains historical SVG coordinates and read-only selection behavior', async () => {
    const w=await create({compact:true,historical:true,readOnly:true,routeCoordinates:[[10,20],[30,40]],historyStatus:'completed'})
    expect(w.get('.estimate-route').attributes('points')).toBe('10,20 30,40')
    expect(w.findAll('.map-controls button').map(button=>button.attributes('aria-label'))).toEqual(['重設','放大地圖','縮小地圖'])
    await w.get('.map-controls button[aria-label="放大地圖"]').trigger('click')
    expect(w.get('.map-world').attributes('transform')).not.toBe('translate(0 0) scale(1)')
    await w.get('.map-controls button[aria-label="重設"]').trigger('click')
    expect(w.get('.map-world').attributes('transform')).toBe('translate(0 0) scale(1)')
    expect(w.findAll('.room-region')).toHaveLength(0)
    await w.get('[data-waypoint="lab"]').trigger('keydown',{key:'Enter'})
    expect(w.emitted('select-destination')).toBeUndefined()
    expect(fetch).toHaveBeenCalledTimes(1)
  })
  it('shows a data error instead of a silently empty map', async () => {
    vi.stubGlobal('fetch',vi.fn(async()=>({ok:false})))
    const w=mount(HospitalMiniMap,{props:{robots}});wrappers.push(w);await flushPromises()
    expect(w.text()).toContain('導航資料載入失敗')
  })
})
