import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import navigation from '../public/generated/rmf-navigation.json'
import TaskRouteProgressPanel from '@/components/overview/TaskRouteProgressPanel.vue'
import { buildActiveRoutes } from '@/data/demoActiveRoutes.js'
import { demoFleetStore } from '@/stores/demoFleetStore.js'

describe('Overview task route progress panel', () => {
  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('loads current Graph 0 without cache and renders the real route vertex order', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: true, json: async () => navigation })
    const wrapper = mount(TaskRouteProgressPanel)
    await flushPromises()
    const route = buildActiveRoutes(navigation, demoFleetStore.tasks.value).find((entry) => entry.taskId === 'T001')
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('rmf-navigation.json'), { cache: 'no-store' })
    expect(wrapper.findAll('.task-route-progress__stops li')).toHaveLength(route.vertexIds.length)
    expect(wrapper.text()).toContain('目前 3 / 5')
    expect(wrapper.text()).toContain('Pharmacy')
    expect(wrapper.text()).toContain('Nurse Reception')
    route.vertexIds.filter((id) => !navigation.vertices.find((vertex) => vertex.id === id)?.name).forEach((id) => {
      expect(wrapper.text()).toContain(`路線點 ${id}`)
    })
    wrapper.unmount()
  })

  it('animates from zero to the real waypoint ratio and reveals completed nodes in order', async () => {
    vi.useFakeTimers()
    vi.spyOn(globalThis, 'requestAnimationFrame').mockImplementation((callback) => { callback(); return 1 })
    vi.spyOn(globalThis, 'cancelAnimationFrame').mockImplementation(() => {})
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: true, json: async () => navigation })
    const wrapper = mount(TaskRouteProgressPanel)
    await flushPromises()

    expect(wrapper.find('.task-route-progress').attributes('style')).toContain('--task-progress-ratio: 0.5')
    vi.advanceTimersByTime(0)
    await wrapper.vm.$nextTick()
    expect(wrapper.findAll('.task-route-progress__stops li.is-revealed')).toHaveLength(1)
    vi.advanceTimersByTime(100)
    await wrapper.vm.$nextTick()
    expect(wrapper.findAll('.task-route-progress__stops li.is-revealed')).toHaveLength(2)
    vi.advanceTimersByTime(1000)
    await wrapper.vm.$nextTick()
    expect(wrapper.findAll('.task-route-progress__stops li.is-revealed')).toHaveLength(3)
    expect(wrapper.findAll('.task-route-progress__stops li')).toHaveLength(5)
    wrapper.unmount()
  })

  it('uses a keyboard-operable custom Morandi listbox instead of a native select', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: true, json: async () => navigation })
    const wrapper = mount(TaskRouteProgressPanel)
    await flushPromises()

    expect(wrapper.find('select').exists()).toBe(false)
    const trigger = wrapper.find('.task-select-trigger')
    expect(trigger.attributes('role')).toBe('combobox')
    await trigger.trigger('keydown', { key: 'ArrowDown' })
    expect(wrapper.find('[role="listbox"]').exists()).toBe(true)
    await trigger.trigger('keydown', { key: 'ArrowDown' })
    await trigger.trigger('keydown', { key: 'Enter' })
    expect(wrapper.find('[role="listbox"]').exists()).toBe(false)
    expect(wrapper.find('.task-select-trigger').text()).toContain('T003')
    wrapper.unmount()
  })
})
