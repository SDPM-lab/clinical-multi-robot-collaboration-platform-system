import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import RobotFleetView from '@/views/RobotFleetView.vue'
import { setLocale } from '@/i18n/index.js'

const api = vi.hoisted(() => ({ getRobotSnapshot: vi.fn(), getTaskRecords: vi.fn() }))
vi.mock('@/services/taskApi.js', () => ({ taskApi: api }))

const ids = ['robot-a', 'robot-b', ...Array.from({ length: 5 }, (_, index) => `robot-hospital_robot_${index + 3}`)]
const snapshot = { robots: ids.map((id, index) => ({
  id, levelName: 'L1', robotType: index < 2 ? 'clean' : index < 4 ? 'medical' : 'ward',
  model: 'agibot_g1', manufacturer: 'Agibot', descriptionPackage: 'agibot_g1_description',
  capabilities: index < 2 ? ['waste_transport', 'clothes_collection'] : index < 4
    ? ['specimen_delivery', 'medication_delivery'] : ['medication_delivery', 'ward_service'],
  status: '離線', hasTelemetry: false, battery: 0, location: '',
})) }
const wrappers = []
async function view() {
  const wrapper = mount(RobotFleetView, { attachTo: document.body, global: { stubs: {
    RobotViewport: { props: ['robotId', 'modelAssetKey'], template: '<div class="robot-viewport-stub" :data-model-asset-key="modelAssetKey" />' },
  } } })
  wrappers.push(wrapper)
  await flushPromises()
  return wrapper
}
beforeEach(() => { setLocale('zh-TW'); api.getRobotSnapshot.mockResolvedValue(snapshot); api.getTaskRecords.mockResolvedValue([]) })
afterEach(() => { wrappers.splice(0).forEach(wrapper => wrapper.unmount()); vi.clearAllMocks() })

describe('Robot Status backend alignment', () => {
  it('shows the seven registered robots without redundant telemetry details or demo battery values', async () => {
    const wrapper = await view()
    expect(wrapper.findAll('.robot-list-item')).toHaveLength(7)
    expect(wrapper.get('.robot-viewport-stub').attributes('data-model-asset-key')).toBe('AGIBOT_A2D')
    expect(wrapper.find('.robot-floor-filter').text()).toContain('1F7')
    expect(wrapper.find('.robot-floor-filter').text()).not.toContain('2F')
    expect(wrapper.findAll('.robot-list-item__battery strong').map(item => item.text())).toEqual(Array(7).fill('—'))
    expect(wrapper.find('.battery-reading strong').text()).toBe('—')
    expect(wrapper.find('.robot-info-card').text()).toContain('清潔型')
    expect(wrapper.find('.robot-info-card').text()).toContain('Agibot Genie G1')
    expect(wrapper.find('.robot-info-card').text()).toContain('agibot_g1_description')
    expect(wrapper.find('.robot-info-card').text()).not.toContain('所需能力')
    expect(wrapper.find('.robot-info-card .robot-info-card__structure').exists()).toBe(true)
    expect(wrapper.find('.robot-telemetry-data').exists()).toBe(false)
    expect(wrapper.get('.robot-info-card__connection').attributes('data-state')).toBe('disconnected')
  })

  it('uses telemetry battery and the backend task code when available', async () => {
    api.getRobotSnapshot.mockResolvedValue({ robots: [{ ...snapshot.robots[0], status: '執行任務中', hasTelemetry: true, lastUpdate: new Date().toISOString(), battery: 82, location: 'nurse_station' }, ...snapshot.robots.slice(1)] })
    api.getTaskRecords.mockResolvedValue([{ taskCode: 'T0001', assignedRobot: 'robot-a', status: 'running' }])
    const wrapper = await view()
    expect(wrapper.find('.robot-list-item__battery strong').text()).toBe('82%')
    expect(wrapper.find('.robot-info-card').text()).toContain('T0001')
    expect(wrapper.find('.robot-info-card').text()).toContain('已連線')
    expect(wrapper.find('.robot-telemetry-data').exists()).toBe(false)
  })

  it('avoids reporting stale robot telemetry as connected', async () => {
    api.getRobotSnapshot.mockResolvedValue({ robots: [{ ...snapshot.robots[0], status: '執行任務中', hasTelemetry: true, lastUpdate: new Date(Date.now() - 16_000).toISOString(), battery: 82 }, ...snapshot.robots.slice(1)] })
    const wrapper = await view()
    expect(wrapper.get('.robot-info-card__connection').attributes('data-state')).toBe('disconnected')
  })

  it('keeps the backend roster fixed in the status page', async () => {
    const wrapper = await view()
    expect(wrapper.find('.edit-robots').exists()).toBe(false)
    expect(wrapper.find('.add-robot').exists()).toBe(false)
  })
})
