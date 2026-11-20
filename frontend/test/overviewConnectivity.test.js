import { nextTick } from 'vue'
import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import NetworkStatusPanel from '@/components/overview/NetworkStatusPanel.vue'
import RobotConnectionPanel from '@/components/overview/RobotConnectionPanel.vue'
import { setLocale } from '@/i18n/index.js'

afterEach(() => setLocale('zh-TW'))

describe('overview connectivity', () => {
  it('never infers healthy network state from missing data', async () => {
    setLocale('en')
    const w = mount(NetworkStatusPanel)
    expect(w.text()).toContain('Unavailable')
    await w.setProps({ status: 'online' }); expect(w.text()).toContain('Online')
    await w.setProps({ status: 'offline' }); expect(w.text()).toContain('Offline')
    await w.setProps({ status: 'connected' }); expect(w.text()).toContain('Unavailable')
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
