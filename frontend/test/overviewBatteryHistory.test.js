import { effectScope, nextTick, ref } from 'vue'
import { mount } from '@vue/test-utils'
import { expect, it, vi } from 'vitest'
import { useOverviewBatteryHistory } from '@/composables/useOverviewBatteryHistory.js'
import BuildingTrendPanel from '@/components/overview/BuildingTrendPanel.vue'
import { robotIds } from '@/data/overviewStatusData.js'
it('bounds telemetry, isolates floors, deduplicates unrelated updates, and stops on scope disposal', async () => {
  const scope = effectScope()
  const status = ref({ floor1: { R01: { robotId: 'R01', battery: 82, updatedAt: 't0' } } })
  const history = scope.run(() => useOverviewBatteryHistory(status))
  for (let i = 1; i < 36; i++) {
    status.value.floor1.R01.updatedAt = `t${i}`
    await nextTick()
  }
  expect(history.floor1.R01).toHaveLength(30)
  status.value.floor1.R01.currentTask = 'changed'
  await nextTick()
  expect(history.floor1.R01).toHaveLength(30)
  status.value = { floor2: { R01: { robotId: 'R01', battery: 71, updatedAt: 't36' } } }
  await nextTick()
  expect(history.floor2.R01[0].value).toBe(71)
  expect(history.floor1.R01.at(-1).value).toBe(82)
  scope.stop()
  status.value.floor2.R01.battery = 60
  await nextTick()
  expect(history.floor2.R01).toHaveLength(1)
})
it('shows hourly labels and the actual reading time in bar details', () => {
  const wrapper = mount(BuildingTrendPanel, { props: { history: { floor1: [{ time: '08:00', observedTimes: { [robotIds[0]]: '08:41' }, batteries: { [robotIds[0]]: 82 } }] } } })
  const chart = wrapper.findAll('.floor-chart')[0]
  expect(chart.findAll('svg text').map(label => label.text())).toEqual(['0', '50', '100', '08:00'])
  expect(chart.get('.robot-bar title').text()).toContain('08:41')
  expect(chart.get('.robot-bar title').text()).toContain('82%')
  wrapper.unmount()
})
it('omits crowded time labels on a narrow chart without hiding battery bars', async () => {
  let resize
  vi.stubGlobal('ResizeObserver', class {
    constructor(callback) { resize = callback }
    observe() {}
    disconnect() {}
  })
  const rows = Array.from({ length: 5 }, (_, i) => ({ time: `${String(i + 8).padStart(2, '0')}:00`, batteries: { [robotIds[0]]: 80 } }))
  const wrapper = mount(BuildingTrendPanel, { props: { history: { floor1: rows } } })
  try {
    resize([{ contentRect: { width: 200, height: 180 } }])
    await nextTick()
    const chart = wrapper.findAll('.floor-chart')[0]
    const labels = chart.findAll('.time-label')
    expect(chart.findAll('.robot-bar')).toHaveLength(5)
    expect(labels.map(label => label.text())).toEqual(['08:00', '10:00', '12:00'])
    expect(Number(labels[1].attributes('x')) - Number(labels[0].attributes('x'))).toBeGreaterThanOrEqual(42)
  } finally {
    wrapper.unmount()
    vi.unstubAllGlobals()
  }
})
