import { afterEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  isReady: vi.fn(),
  mount: vi.fn(),
  use: vi.fn(),
  installTranslation: vi.fn(),
}))

vi.mock('vue', () => ({ createApp: () => ({ use: mocks.use, mount: mocks.mount }) }))
vi.mock('@/router', () => ({ default: { isReady: mocks.isReady } }))
vi.mock('@/App.vue', () => ({ default: {} }))
vi.mock('@/config/visualTokens.js', () => ({ installVisualTokens: vi.fn() }))
vi.mock('@/i18n/index.js', () => ({
  i18n: { global: { locale: { value: 'en' } } },
  installGlobalTranslation: mocks.installTranslation,
}))

afterEach(() => {
  vi.restoreAllMocks()
  vi.clearAllMocks()
  vi.resetModules()
  document.body.innerHTML = ''
})

describe('startup loading', () => {
  it('remains visible until the initial route is ready', async () => {
    let finish
    mocks.isReady.mockReturnValue(new Promise(resolve => { finish = resolve }))
    mocks.use.mockReturnThis()
    document.body.innerHTML = '<div id="startup-loading"></div><div id="app"></div>'

    await import('@/main.js')
    expect(document.getElementById('startup-loading')).not.toBeNull()
    finish()
    await Promise.resolve()
    expect(document.getElementById('startup-loading')).toBeNull()
  })

  it('shows an error when the initial route fails', async () => {
    mocks.isReady.mockRejectedValue(new Error('router failed'))
    mocks.use.mockReturnThis()
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    document.body.innerHTML = '<div id="startup-loading"></div><div id="app"></div>'

    await import('@/main.js')
    await Promise.resolve()
    expect(document.getElementById('startup-loading').getAttribute('role')).toBe('alert')
    expect(document.getElementById('startup-loading').textContent).toContain('Unable to load')
    expect(consoleError).toHaveBeenCalled()
  })
})
