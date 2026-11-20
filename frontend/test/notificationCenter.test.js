import { afterEach, describe, expect, it } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import NotificationCenter from '@/components/NotificationCenter.vue'
import { notificationStore } from '@/stores/notificationStore.js'
import { setLocale } from '@/i18n/index.js'

afterEach(() => { notificationStore.clear(); setLocale('zh-TW') })
describe('notification center', () => {
  it('keeps task messages after their toast disappears and translates them on language change', async () => {
    notificationStore.add({ key: 'dispatch.created', params: { id: 'T0001' }, taskTitle: '藥品配送', type: 'success' })
    const wrapper = mount(NotificationCenter)
    expect(wrapper.get('.notification-badge').text()).toBe('1')
    await wrapper.get('.notification-root').trigger('mouseenter')
    expect(wrapper.get('.notification-panel').text()).toContain('T0001')
    expect(wrapper.find('.notification-badge').exists()).toBe(false)
    setLocale('en'); await flushPromises()
    expect(wrapper.get('.notification-panel').text()).toContain('Medication delivery')
    await wrapper.get('.notification-panel header button').trigger('click')
    expect(wrapper.get('.notification-panel').text()).toContain('No notifications yet')
    wrapper.unmount()
  })
  it('opens by click and closes on Escape', async () => {
    const wrapper = mount(NotificationCenter, { attachTo: document.body })
    await wrapper.get('.notification-bell').trigger('click')
    expect(wrapper.find('.notification-panel').exists()).toBe(true)
    await wrapper.get('.notification-root').trigger('keydown', { key: 'Escape' })
    expect(wrapper.find('.notification-panel').exists()).toBe(false)
    wrapper.unmount()
  })
})
