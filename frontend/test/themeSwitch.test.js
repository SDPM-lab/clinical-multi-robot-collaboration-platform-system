import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'

import AppShellView from '@/views/AppShellView.vue'

const createTestRouter = async () => {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'overview', component: { template: '<div />' } },
      { path: '/login', name: 'login', component: { template: '<div />' } },
      { path: '/task-logs', name: 'task-logs', component: { template: '<div />' } },
    ],
  })
  await router.push('/')
  await router.isReady()
  return router
}

describe('theme switching', () => {
  afterEach(() => {
    localStorage.removeItem('hospital-rmf-color-theme')
    document.documentElement.dataset.theme = 'light'
    window.history.replaceState({}, '', '/')
  })

  it('opens Robot Status from the dedicated debug URL', async () => {
    window.history.replaceState({}, '', '/?robotDebug=1&cameraDebug=1&modelDebug=1')
    const router = await createTestRouter()
    const wrapper = mount(AppShellView, {
      global: {
        plugins: [router],
        stubs: {
          RobotFleetView: { template: '<div class="robot-view-stub" />' },
          HospitalScene: true,
        },
      },
    })

    expect(wrapper.find('.robot-view-stub').exists()).toBe(true)
    wrapper.unmount()
  })

  it('switches light and dark twice without leaving a transition overlay behind', async () => {
    localStorage.setItem('hospital-rmf-color-theme', 'light')
    const router = await createTestRouter()
    const wrapper = mount(AppShellView, {
      global: {
        plugins: [router],
        stubs: {
          ClinicOverviewView: true,
          OverviewSearch: true,
        },
      },
    })
    const toggle = wrapper.get('.theme-toggle')

    expect(document.documentElement.dataset.theme).toBe('light')
    for (const expected of ['dark', 'light', 'dark', 'light']) {
      await toggle.trigger('click')
      expect(document.documentElement.dataset.theme).toBe(expected)
      expect(wrapper.find('.theme-overlay').exists()).toBe(false)
      expect(wrapper.find('.dark-overlay').exists()).toBe(false)
    }

    wrapper.unmount()
  })

  it('keeps dispatch, robot status, and schedule history renderable with the global background', async () => {
    const router = await createTestRouter()
    const wrapper = mount(AppShellView, {
      global: {
        plugins: [router],
        stubs: {
          ClinicOverviewView: true,
          OverviewSearch: true,
          TaskDispatchView: { template: '<div class="dispatch-view-stub" />' },
          RobotFleetView: { template: '<div class="robot-view-stub" />' },
          ScheduleHistoryView: { template: '<div class="schedule-history-view-stub" />' },
          HospitalScene: true,
        },
      },
    })
    const navButton = (label) => wrapper.findAll('.overview-nav__link').find((button) => button.text() === label)

    await navButton('任務派遣').trigger('click')
    expect(wrapper.find('.dispatch-view-stub').exists()).toBe(true)
    expect(wrapper.get('.overview-page').exists()).toBe(true)
    expect(wrapper.find('.route-background-stub').exists()).toBe(false)

    await navButton('機器人狀態').trigger('click')
    expect(wrapper.find('.robot-view-stub').exists()).toBe(true)

    await navButton('排程歷史').trigger('click')
    expect(wrapper.find('.schedule-history-view-stub').exists()).toBe(true)

    wrapper.unmount()
  })
})
