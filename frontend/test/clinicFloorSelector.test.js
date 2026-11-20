import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { describe, expect, it } from 'vitest'
import FloorSelector from '@/components/overview/FloorSelector.vue'
import { setLocale } from '@/i18n/index.js'

describe('clinic floor projected labels', () => {
  it('draws connectors to projected Three.js floor coordinates', async () => {
    const wrapper = mount(FloorSelector, {
      props: {
        modelValue: 2,
        anchors: {
          1: { x: 410, y: 480, visible: true },
          2: { x: 430, y: 405, visible: true },
          3: { x: 450, y: 330, visible: true },
        },
      },
    })
    const activeLine = wrapper.get('g.is-active line')
    expect(activeLine.attributes('x1')).toBe('282')
    expect(activeLine.attributes('y1')).toBe('115')
    expect(activeLine.attributes('x2')).toBe('430')
    expect(activeLine.attributes('y2')).toBe('405')

    await wrapper.setProps({ anchors: { ...wrapper.props('anchors'), 2: { x: 510, y: 390, visible: true } } })
    expect(wrapper.get('g.is-active line').attributes('x2')).toBe('510')
  })

  it('localizes the all-building tab in English and Traditional Chinese', async () => {
    const wrapper = mount(FloorSelector)
    expect(wrapper.get('.all-floor').text()).toBe('全部全棟')
    setLocale('en')
    await nextTick()
    expect(wrapper.get('.all-floor').text()).toBe('AllBuilding')
    setLocale('zh-TW')
    await nextTick()
    expect(wrapper.get('.all-floor').text()).toBe('全部全棟')
    wrapper.unmount()
  })
})

it('renders only the clicked floor connector and never creates lines on hover', async () => {
  const wrapper = mount(FloorSelector, { props: { modelValue: 'all', anchors: {
    1: { x: 410, y: 480, visible: true },
    2: { x: 430, y: 405, visible: true },
    3: { x: 450, y: 330, visible: true },
  } } })
  expect(wrapper.findAll('line')).toHaveLength(0)
  await wrapper.get('.floor-label').trigger('mouseenter')
  expect(wrapper.findAll('line')).toHaveLength(0)
  expect(wrapper.emitted('update:modelValue')).toBeUndefined()
  await wrapper.get('.floor-label').trigger('click')
  expect(wrapper.emitted('update:modelValue')[0]).toEqual([1])
  await wrapper.setProps({ modelValue: 3 })
  expect(wrapper.findAll('line')).toHaveLength(1)
  await wrapper.setProps({ modelValue: 2 })
  expect(wrapper.findAll('line')).toHaveLength(1)
  expect(wrapper.get('line').attributes('x2')).toBe('430')
  await wrapper.setProps({ modelValue: 'all' })
  expect(wrapper.find('svg').exists()).toBe(false)
  wrapper.unmount()
})
