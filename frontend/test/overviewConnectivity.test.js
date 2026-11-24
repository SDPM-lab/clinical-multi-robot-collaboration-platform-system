import { nextTick } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import NetworkStatusPanel from '@/components/overview/NetworkStatusPanel.vue'
import RobotConnectionPanel from '@/components/overview/RobotConnectionPanel.vue'
import ClinicOverviewView from '@/views/ClinicOverviewView.vue'
import { taskApi } from '@/services/taskApi.js'
import { setLocale } from '@/i18n/index.js'

afterEach(() => { setLocale('zh-TW'); vi.restoreAllMocks(); vi.unstubAllGlobals() })

describe('overview connectivity', () => {
  it('never infers healthy network state from missing data', async () => {
    setLocale('en')
    const w = mount(NetworkStatusPanel)
    expect(w.text()).toContain('Unavailable')
    await w.setProps({ status: 'connected' })
    expect(w.text()).toContain('ROS 2 connected')
    expect(w.attributes('data-state')).toBe('online')
    await w.setProps({ status: 'connecting' })
    expect(w.text()).toContain('ROS 2 connecting')
    await w.setProps({ status: 'disconnected' })
    expect(w.text()).toContain('ROS 2 disconnected')
    expect(w.attributes('data-state')).toBe('offline')
    w.unmount()
  })
  it('uses the robot API for both overview cards even if the task API fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false }))
    vi.spyOn(taskApi, 'getRobotSnapshot').mockResolvedValue({
      connection: { status: 'connected' },
      robots: [{ hasTelemetry: true, status: '待命' }, { hasTelemetry: false, status: '離線' }],
    })
    vi.spyOn(taskApi, 'getTaskRecords').mockRejectedValue(new Error('Tasks unavailable'))
    const w = mount(ClinicOverviewView, { global: { stubs: { ClinicOverviewScene: true } } })
    await flushPromises()
    expect(w.get('.connectivity-panel[data-state]').attributes('data-state')).toBe('online')
    expect(w.get('.connection-count').attributes('aria-label')).toBe('1 / 2')
    w.unmount()
  })
  it('counts communication states, handles unknown sources, and updates without animation for reduced motion', async () => {
    setLocale('en')
    const previous = window.matchMedia
    window.matchMedia = vi.fn(() => ({ matches: true }))
    const w = mount(RobotConnectionPanel, { props: { robots: [{ state: 'executing', connectionState: 'disconnected' }, { connectionState: 'connected' }, { connectionState: 'connecting' }] } })
    await nextTick()
    expect(w.get('.connection-count').attributes('aria-label')).toBe('1 / 3')
    expect(w.get('.connection-count strong').text()).toBe('1')
    await w.setProps({ robots: [{ connectionState: 'connected' }, { connectionState: 'connected' }] })
    expect(w.get('.connection-count strong').text()).toBe('2')
    await w.setProps({ robots: [{ state: 'executing' }] })
    expect(w.text()).toContain('Unavailable')
    setLocale('zh-TW')
    await nextTick()
    expect(w.text()).toContain('未提供')
    w.unmount(); window.matchMedia = previous
  })
})
