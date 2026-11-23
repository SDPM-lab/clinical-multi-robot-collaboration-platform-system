import { describe, expect, it, vi } from 'vitest'

const state = vi.hoisted(() => ({
  authenticated: { value: false },
  loginLoaded: vi.fn(),
  shellLoaded: vi.fn(),
}))

vi.mock('@/stores/authStore.js', () => ({
  authStore: { authenticated: state.authenticated, initialize: vi.fn().mockResolvedValue() },
}))
vi.mock('@/views/LoginView.vue', () => {
  state.loginLoaded()
  return { default: { template: '<div>Login</div>' } }
})
vi.mock('@/views/AppShellView.vue', () => {
  state.shellLoaded()
  return { default: { template: '<div>App</div>' } }
})

describe('lazy routes', () => {
  it('loads the login page without the app shell, then loads the shell after authentication', async () => {
    const { default: router } = await import('@/router/index.js')
    await router.push('/')
    expect(router.currentRoute.value.name).toBe('login')
    expect(state.loginLoaded).toHaveBeenCalledOnce()
    expect(state.shellLoaded).not.toHaveBeenCalled()

    state.authenticated.value = true
    await router.push('/')
    expect(router.currentRoute.value.name).toBe('overview')
    expect(state.shellLoaded).toHaveBeenCalledOnce()
  })
})
