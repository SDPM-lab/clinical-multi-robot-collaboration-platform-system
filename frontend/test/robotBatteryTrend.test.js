import { nextTick } from 'vue'
import { mount } from '@vue/test-utils'
import { expect, it } from 'vitest'
import { fixedDemoBatteryHistory, selectBatteryHistory } from '@/data/robotBatteryTrend.js'
import FloorRobotStatusPanel from '@/components/overview/FloorRobotStatusPanel.vue'
import RobotBatteryTrend from '@/components/overview/RobotBatteryTrend.vue'

const now = new Date(2026, 8, 16, 16).getTime()
const row = (date, battery) => ({ timestamp: date.getTime(), batteries: { R01: battery } })

it('uses latest real samples in Day, Weekly and Monthly without future points', () => {
  const history = [
    row(new Date(2026, 8, 14, 10, 5), 88), row(new Date(2026, 8, 14, 10, 50), 84),
    row(new Date(2026, 8, 15, 13), 80), row(new Date(2026, 8, 13, 12), 91),
    row(new Date(2026, 7, 12), 96), row(new Date(2026, 8, 17), 79),
  ]
  expect(selectBatteryHistory(history, {}, 'R01', 'Day', now).map((point) => point.value)).toEqual([80])
  expect(selectBatteryHistory(history, {}, 'R01', 'Weekly', now).map((point) => point.value)).toEqual([91, 84, 80])
  expect(selectBatteryHistory(history, {}, 'R01', 'Monthly', now).map((point) => point.value)).toEqual([91, 84, 80])
  expect(selectBatteryHistory(history, {}, 'R03', 'Weekly', now)).toEqual([])
})

it('provides stable demo histories with task metadata', () => {
  const first = fixedDemoBatteryHistory('R01', 'Day')
  expect(fixedDemoBatteryHistory('R01', 'Day')).toEqual(first)
  expect(first).toHaveLength(7)
  expect(first.at(-1)).toMatchObject({ value: 82, task: '藥品配送', taskId: 'T001', status: 'executing' })
  expect(fixedDemoBatteryHistory('R02', 'Day').at(-1).value).toBe(34)
  expect(fixedDemoBatteryHistory('R03', 'Day').at(-1).value).toBe(18)
  expect(fixedDemoBatteryHistory('R01', 'Day', { value: 79, timestamp: 1234, task: '真實任務', taskId: 'T099' }).at(-1)).toMatchObject({ value: 79, timestamp: 1234, task: '真實任務', taskId: 'T099' })
})

it('renders three independent charts, ranges, batteries and an expandable dialog', async () => {
  const robots = Object.fromEntries(['R01', 'R02', 'R03'].map((id, index) => [id, {
    robotId: id, name: `Robot 0${index + 1}`, status: ['executing', 'charging', 'idle'][index],
    battery: [82, 34, 18][index], currentTask: ['藥品配送', '檢驗報告運送', '病房物資補充'][index],
    taskId: ['T001', 'T014', 'T021'][index],
  }]))
  const wrapper = mount(FloorRobotStatusPanel, { props: { floor: 'floor1', robots, demo: true }, attachTo: document.body })
  expect(wrapper.findAll('.robot-trend-column')).toHaveLength(3)
  expect(wrapper.findAll('.robot-battery-trend')).toHaveLength(3)
  expect(wrapper.findAll('.battery-range-tabs')).toHaveLength(3)
  expect(wrapper.findAll('.battery-segments span')).toHaveLength(30)
  expect(wrapper.findAll('.battery-tooltip')).toHaveLength(3)
  expect(wrapper.findAll('img')).toHaveLength(0)
  expect(wrapper.findAll('.latest-status')[0].text()).toBe('執行中 · 藥品配送 · T001')
  expect(wrapper.findAll('.battery-tooltip')[0].text()).toContain('2026-09-14')
  expect(wrapper.findAll('.battery-tooltip')[0].text()).toContain('14:00:00')
  expect(wrapper.findAll('.battery-tooltip')[0].text()).toContain('藥品配送 · T001')
  expect(wrapper.findAll('.battery-tooltip')[0].text()).toContain('電量 82%')
  await wrapper.findAll('.battery-range-tabs button')[1].trigger('click')
  expect(wrapper.findAll('.battery-range-tabs button')[1].attributes('aria-pressed')).toBe('true')
  expect(wrapper.findAll('.battery-range-tabs button')[4].attributes('aria-pressed')).toBe('false')
  await wrapper.findAll('.expand-button')[0].trigger('click')
  expect(document.body.querySelector('.battery-dialog')).not.toBeNull()
  expect(document.body.querySelector('.battery-dialog .battery-range-tabs button[aria-pressed="true"]').textContent).toBe('Weekly')
  document.body.querySelector('.dialog-close').click()
  await nextTick()
  expect(document.body.querySelector('.battery-dialog')).toBeNull()
  wrapper.unmount()
})

it('defaults to latest tooltip, follows nearest points and returns on leave', async () => {
  const points = [
    { value: 82, timestamp: Date.parse('2026-09-14T13:00:00+08:00'), task: '藥品配送', taskId: 'T001' },
    { value: 76, timestamp: Date.parse('2026-09-14T14:00:00+08:00'), task: '藥品配送', taskId: 'T001' },
  ]
  const wrapper = mount(RobotBatteryTrend, { props: { robotName: 'Robot 01', range: 'Day', points, color: '#F28A32' } })
  wrapper.element.getBoundingClientRect = () => ({ left: 0, width: 360 })
  expect(wrapper.get('.battery-tooltip').text()).toContain('2026-09-14')
  expect(wrapper.get('.battery-tooltip').text()).toContain('14:00:00')
  expect(wrapper.get('.status-pointer').attributes('style')).toContain('342px')
  wrapper.element.dispatchEvent(new MouseEvent('pointermove', { clientX: 35, bubbles: true }))
  await nextTick()
  expect(wrapper.get('.battery-tooltip').text()).toContain('13:00:00')
  await wrapper.trigger('pointerleave')
  expect(wrapper.get('.battery-tooltip').text()).toContain('14:00:00')
  expect(wrapper.get('.trend-line').attributes('d')).toMatch(/342,[\d.]+$/)
  expect(wrapper.find('[stroke-dasharray]').exists()).toBe(false)
  wrapper.unmount()
})
