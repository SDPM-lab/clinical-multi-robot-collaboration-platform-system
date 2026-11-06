import { mount } from '@vue/test-utils'
import { afterEach, expect, it, vi } from 'vitest'
import F1SpeedGauge from '@/components/overview/F1SpeedGauge.vue'

afterEach(() => vi.unstubAllGlobals())
it('maps progress to the needle angle and updates the same gauge in reduced motion', async () => {
  vi.stubGlobal('matchMedia', () => ({ matches: true }))
  const wrapper = mount(F1SpeedGauge, { props: { value: 0 } })
  const svg = wrapper.get('svg').element
  expect(wrapper.get('.speed-needle').attributes('transform')).toBe('rotate(-90 120 108)')
  for (const [value, angle] of [[50, 0], [100, 90], [86, 64.80000000000001], [120, 90], [-1, -90]]) {
    await wrapper.setProps({ value })
    expect(wrapper.get('.speed-needle').attributes('transform')).toBe(`rotate(${angle} 120 108)`)
    expect(wrapper.get('svg').element).toBe(svg)
  }
  wrapper.unmount()
})

it.each([18, 34, 64, 86])('renders one orange and yellow gradient arc at %s percent', async (value) => {
  vi.stubGlobal('matchMedia', () => ({ matches: true }))
  const wrapper = mount(F1SpeedGauge, { props: { value } })
  await wrapper.vm.$nextTick()
  const arcs = wrapper.findAll('.speed-arc')
  expect(arcs).toHaveLength(1)
  expect(arcs[0].attributes('stroke-dasharray')).toBe(`${value} 100`)
  expect(wrapper.findAll('stop').map(stop => stop.attributes('stop-color'))).toEqual(['var(--overview-accent)', 'var(--overview-accent)', 'var(--overview-yellow)'])
  expect(wrapper.findAll('.speed-track')).toHaveLength(1)
  expect(wrapper.findAll('.speed-ticks line')).toHaveLength(37)
  expect(wrapper.find('.speed-core').exists()).toBe(true)
  wrapper.unmount()
})
