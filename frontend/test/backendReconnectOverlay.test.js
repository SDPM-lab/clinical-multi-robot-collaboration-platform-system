import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import BackendReconnectOverlay from '@/components/BackendReconnectOverlay.vue'
import { setLocale } from '@/i18n/index.js'
import { sessionFetch } from '@/services/sessionApi.js'

vi.mock('@/services/sessionApi.js', () => ({ apiBaseUrl: '', sessionFetch: vi.fn() }))

afterEach(() => {
  vi.useRealTimers()
  vi.clearAllMocks()
  setLocale('zh-TW')
})

describe('backend reconnect overlay', () => {
  it('keeps the page visible, shows disconnection and clears it after recovery', async () => {
    vi.useFakeTimers()
    sessionFetch.mockResolvedValueOnce({ ok: true, status: 200 })
      .mockRejectedValueOnce(new Error('connection lost'))
      .mockResolvedValueOnce({ ok: false, status: 502 })
      .mockResolvedValueOnce({ ok: true, status: 200 })
    const wrapper = mount(BackendReconnectOverlay)
    await vi.advanceTimersByTimeAsync(0)
    expect(wrapper.find('[role="status"]').exists()).toBe(false)

    await vi.advanceTimersByTimeAsync(5000)
    expect(wrapper.get('[role="status"]').text()).toContain('重新連線中')
    await vi.advanceTimersByTimeAsync(5000)
    expect(wrapper.get('[role="status"]').exists()).toBe(true)
    await vi.advanceTimersByTimeAsync(5000)
    expect(wrapper.find('[role="status"]').exists()).toBe(false)

    wrapper.unmount()
    await vi.advanceTimersByTimeAsync(10000)
    expect(sessionFetch).toHaveBeenCalledTimes(4)
  })

  it('aborts an in-flight check when the page is closed', async () => {
    vi.useFakeTimers()
    let signal
    sessionFetch.mockImplementation((_url, options) => {
      signal = options.signal
      return new Promise(() => {})
    })
    const wrapper = mount(BackendReconnectOverlay)
    expect(signal.aborted).toBe(false)
    wrapper.unmount()
    expect(signal.aborted).toBe(true)
    await vi.advanceTimersByTimeAsync(10000)
    expect(sessionFetch).toHaveBeenCalledOnce()
  })

  it('shows reconnecting when a check times out and retries after the timeout', async () => {
    vi.useFakeTimers()
    sessionFetch.mockImplementationOnce((_url, options) => new Promise((_resolve, reject) => {
      options.signal.addEventListener('abort', () => reject(new Error('timeout')))
    })).mockResolvedValueOnce({ ok: true, status: 200 })
    const wrapper = mount(BackendReconnectOverlay)
    await vi.advanceTimersByTimeAsync(5000)
    expect(wrapper.get('[role="status"]').text()).toContain('重新連線中')
    await vi.advanceTimersByTimeAsync(5000)
    expect(wrapper.find('[role="status"]').exists()).toBe(false)
    wrapper.unmount()
  })
})
