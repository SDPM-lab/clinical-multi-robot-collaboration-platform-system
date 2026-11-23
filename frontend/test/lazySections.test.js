import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import AppShellView from '@/views/AppShellView.vue'

const loads = vi.hoisted(() => ({ overview: vi.fn(), dispatch: vi.fn(), history: vi.fn() }))
vi.mock('@/views/ClinicOverviewView.vue', () => {
  loads.overview()
  return { __esModule: true, default: { template: '<div class="overview-loaded" />' } }
})
vi.mock('@/views/TaskDispatchView.vue', () => {
  loads.dispatch()
  return { __esModule: true, default: { template: '<div class="dispatch-loaded" />' } }
})
vi.mock('@/views/ScheduleHistoryView.vue', () => {
  loads.history()
  throw new Error('module unavailable')
})

afterEach(() => {
  vi.restoreAllMocks()
  window.history.replaceState({}, '', '/')
})

describe('lazy app sections', () => {
  it('loads only the active section and reports a failed section import', async () => {
    const router = createRouter({ history: createMemoryHistory(), routes: [
      { path: '/', name: 'overview', component: { template: '<div />' } },
      { path: '/login', name: 'login', component: { template: '<div />' } },
    ] })
    await router.push('/')
    const wrapper = mount(AppShellView, { global: { plugins: [router] } })
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    vi.spyOn(console, 'warn').mockImplementation(() => {})
    await flushPromises()

    expect(wrapper.find('.overview-loaded').exists()).toBe(true)
    expect(loads.dispatch).not.toHaveBeenCalled()
    expect(loads.history).not.toHaveBeenCalled()

    const nav = label => wrapper.findAll('.overview-nav__link').find(button => button.text() === label)
    await nav('任務派遣').trigger('click')
    await flushPromises()
    expect(wrapper.find('.dispatch-loaded').exists()).toBe(true)
    expect(loads.dispatch).toHaveBeenCalledOnce()
    expect(loads.history).not.toHaveBeenCalled()

    await nav('排程歷史').trigger('click')
    await flushPromises()
    expect(loads.history).toHaveBeenCalledOnce()
    expect(wrapper.get('[role="alert"]').text()).toContain('無法載入頁面')
    expect(consoleError).toHaveBeenCalled()
    wrapper.unmount()
  })
})
