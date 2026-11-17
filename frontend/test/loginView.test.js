import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { setLocale } from '@/i18n/index.js'
import LoginView from '@/views/LoginView.vue'
import { authStore } from '@/stores/authStore.js'
vi.mock('@/stores/authStore.js', () => ({ authStore: { login: vi.fn(), loginAsDevelopmentUser: vi.fn(), register: vi.fn() } }))
afterEach(() => { vi.clearAllMocks(); setLocale('zh-TW') })
const setup = async () => {
  const router = createRouter({ history: createMemoryHistory(), routes: [
    { path: '/login', component: LoginView }, { path: '/', component: { template: '<div />' } },
  ] })
  await router.push('/login')
  await router.isReady()
  return { router, wrapper: mount(LoginView, { global: { plugins: [router] } }) }
}
describe('login and registration form', () => {
  it('submits credentials and remembers the session only when selected', async () => {
    const { wrapper, router } = await setup()
    await wrapper.get('#auth-email').setValue('nurse@example.test')
    await wrapper.get('#auth-password').setValue('long-passphrase')
    await wrapper.get('input[name=rememberMe]').setValue(true)
    authStore.login.mockResolvedValue({ id: 'user' })
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(authStore.login).toHaveBeenCalledWith({ email: 'nurse@example.test', password: 'long-passphrase', rememberMe: true })
    expect(router.currentRoute.value.path).toBe('/')
    wrapper.unmount()
  })
  it('validates confirmation before registering and displays both languages', async () => {
    const { wrapper } = await setup()
    await wrapper.get('.auth-tabs button:last-child').trigger('click')
    await wrapper.get('#auth-name').setValue('Nurse Judy')
    await wrapper.get('#auth-email').setValue('nurse@example.test')
    await wrapper.get('#auth-password').setValue('long-passphrase')
    await wrapper.get('#auth-confirmation').setValue('different-password')
    await wrapper.get('form').trigger('submit')
    expect(wrapper.get('[role=alert]').text()).toContain('不一致')
    expect(authStore.register).not.toHaveBeenCalled()
    setLocale('en'); await flushPromises()
    expect(wrapper.get('[role=alert]').text()).toContain('do not match')
    await wrapper.get('#auth-confirmation').setValue('long-passphrase')
    authStore.register.mockResolvedValue({ id: 'user' })
    await wrapper.get('form').trigger('submit'); await flushPromises()
    expect(authStore.register).toHaveBeenCalledWith({ name: 'Nurse Judy', email: 'nurse@example.test', password: 'long-passphrase' })
    wrapper.unmount()
  })
  it('accepts a six-digit numeric password during registration', async () => {
    const { wrapper } = await setup()
    await wrapper.get('.auth-tabs button:last-child').trigger('click')
    await wrapper.get('#auth-name').setValue('Nurse Judy')
    await wrapper.get('#auth-email').setValue('nurse@example.test')
    await wrapper.get('#auth-password').setValue('123456')
    await wrapper.get('#auth-confirmation').setValue('123456')
    authStore.register.mockResolvedValue({ id: 'user' })
    await wrapper.get('form').trigger('submit'); await flushPromises()
    expect(authStore.register).toHaveBeenCalledWith({ name: 'Nurse Judy', email: 'nurse@example.test', password: '123456' })
    wrapper.unmount()
  })
  it('shows understandable errors and unlocks the form after failed sign-in', async () => {
    const { wrapper } = await setup()
    authStore.login.mockRejectedValue({ code: 'invalid_credentials' })
    await wrapper.get('#auth-email').setValue('nurse@example.test')
    await wrapper.get('#auth-password').setValue('incorrect-password')
    await wrapper.get('form').trigger('submit'); await flushPromises()
    expect(wrapper.get('[role=alert]').text()).toContain('電子郵件或密碼不正確')
    expect(wrapper.get('fieldset').attributes('disabled')).toBeUndefined()
    wrapper.unmount()
  })
  it('signs in with the development test account and returns to the requested page', async () => {
    const { wrapper, router } = await setup()
    await router.replace('/login?redirect=%2Fdispatch')
    authStore.loginAsDevelopmentUser.mockResolvedValue({ id: 'dev-user' })
    await wrapper.get('.auth-dev-login').trigger('click')
    await flushPromises()
    expect(authStore.loginAsDevelopmentUser).toHaveBeenCalledOnce()
    expect(router.currentRoute.value.fullPath).toBe('/dispatch')
    wrapper.unmount()
  })
})
