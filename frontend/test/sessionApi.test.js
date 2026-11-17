import { afterEach, describe, expect, it, vi } from 'vitest'
import { authRequest, jsonOptions, resetCsrf, sessionFetch } from '@/services/sessionApi.js'

afterEach(() => { vi.unstubAllGlobals(); resetCsrf() })
describe('authenticated API transport', () => {
  it('fetches a CSRF token and sends cookies and the token with every write', async () => {
    const fetch = vi.fn().mockResolvedValueOnce({ ok: true, json: async () => ({ token: 'csrf-token' }) })
      .mockResolvedValue({ ok: true, status: 204 })
    vi.stubGlobal('fetch', fetch)
    await sessionFetch('/api/v1/task', jsonOptions('POST', { note: 'handoff' }))
    await sessionFetch('/api/v1/task/id', { method: 'DELETE' })
    expect(fetch).toHaveBeenCalledTimes(3)
    expect(fetch.mock.calls[0][0]).toBe('/api/auth/csrf')
    expect(fetch.mock.calls[1][1].credentials).toBe('include')
    expect(fetch.mock.calls[1][1].headers.get('X-CSRF-TOKEN')).toBe('csrf-token')
    expect(fetch.mock.calls[2][1].headers.get('X-CSRF-TOKEN')).toBe('csrf-token')
  })
  it('notifies the app of an expired session without treating invalid login as expiration', async () => {
    const expired = vi.fn()
    window.addEventListener('auth:expired', expired)
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 401 }))
    await sessionFetch('/api/auth/me')
    expect(expired).toHaveBeenCalledTimes(1)
    window.removeEventListener('auth:expired', expired)
  })
  it('preserves server error codes for localized messages', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce({ ok: true, json: async () => ({ token: 'token' }) })
      .mockResolvedValue({ ok: false, status: 409, json: async () => ({ code: 'email_exists' }) }))
    await expect(authRequest('/register', jsonOptions('POST', {}))).rejects.toMatchObject({ code: 'email_exists', status: 409 })
  })
})
