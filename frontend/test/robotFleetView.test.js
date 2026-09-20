import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import RobotFleetView from '@/views/RobotFleetView.vue'
import { fleetStore } from '@/stores/demoFleetStore.js'
import navigation from '../public/generated/rmf-navigation.json'
const wrappers = []
function view() {
  const wrapper = mount(RobotFleetView, { attachTo: document.body, global: { stubs: { RobotViewport: true } } })
  wrappers.push(wrapper)
  return wrapper
}
afterEach(() => { wrappers.splice(0).forEach(w => w.unmount()); vi.restoreAllMocks() })
describe('robot product stage', () => {
  it('uses the fixed control panel to search and switch robots with overview open by default', async () => {
    const w = view()
    expect(w.find('.robot-control-panel').exists()).toBe(true)
    expect(w.find('.robot-control-panel').text()).not.toMatch(/即時狀態|LIVE/)
    expect(w.find('.liquid-battery').exists()).toBe(true)
    expect(w.find('.thermal-arc').exists()).toBe(true)
    expect(w.find('.task-accuracy-card').text()).toContain('尚無已完成任務')
    expect(w.findAll('.robot-list-item__avatar')).toHaveLength(3)
    expect(w.find('.robot-inspector').exists()).toBe(true)
    expect(w.findAll('.robot-inspector-tabs button')).toHaveLength(4)
    expect(w.get('.robot-inspector-tabs button[aria-current="page"]').text()).toBe('概況')
    expect(w.findAll('.robot-picker button')).toHaveLength(3)
    expect(w.findAll('.robot-arrow')).toHaveLength(0)
    await w.findAll('.robot-picker button')[1].trigger('click')
    expect(w.get('.robot-stage-status__name').text()).toBe('Robot 02')
    expect(w.get('.thermal').classes()).toContain('is-warning')
    await w.findAll('.robot-picker button')[2].trigger('click')
    expect(w.get('.robot-stage-status__name').text()).toBe('Robot 03')
    expect(w.get('.thermal').classes()).toContain('is-critical')
    await w.get('.robot-search input').setValue('Robot 02')
    expect(w.findAll('.robot-picker button')).toHaveLength(1)
    expect(w.get('.robot-picker button').text()).toContain('Robot 02')
  })
  it('disables disconnected charging, contains no demo badges and previews real directed lanes without dispatch', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: true, json: async () => navigation })
    const before = JSON.stringify(fleetStore.state)
    const w = view()
    await w.findAll('.robot-inspector-tabs button')[2].trigger('click')
    expect(w.get('.charge-button').attributes('disabled')).toBeDefined()
    expect(w.text()).toContain('控制服務未連線')
    expect(w.text()).not.toMatch(/demo|模擬/i)
    await w.get('.inspector-action').trigger('click')
    await flushPromises()
    const lines = w.findAll('.lane-pending')
    expect(lines.length).toBeGreaterThan(1)
    const byId = new Map(navigation.vertices.map(v => [v.id, v]))
    for (const line of lines) {
      const a = line.attributes()
      expect(navigation.lanes.some(l => {
        const from = byId.get(l.from), to = byId.get(l.to)
        return from.x === Number(a.x1) && from.y === Number(a.y1) && to.x === Number(a.x2) && to.y === Number(a.y2)
      })).toBe(true)
    }
    const destination = navigation.namedWaypoints.find(v => v.name === 'charging_station')
    const final = byId.get(destination.id)
    expect(Number(lines.at(-1).attributes('x2'))).toBe(final.x)
    expect(Number(lines.at(-1).attributes('y2'))).toBe(final.y)
    expect(JSON.stringify(fleetStore.state)).toBe(before)
    expect(w.text()).toContain('尚未派遣')
  })
})
