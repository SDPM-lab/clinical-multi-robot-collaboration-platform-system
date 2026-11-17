import { afterEach, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
vi.mock('three', async importOriginal => ({
  ...await importOriginal(),
  WebGLRenderer: class { constructor() { throw new Error('WebGL context unavailable') } },
}))
import ClinicOverviewScene from '@/components/scene/ClinicOverviewScene.vue'
afterEach(() => vi.restoreAllMocks())
it('shows a recoverable graphics error instead of leaving a blank scene when WebGL setup fails', async () => {
  vi.spyOn(console,'error').mockImplementation(()=>{})
  const wrapper=mount(ClinicOverviewScene)
  await flushPromises()
  expect(wrapper.text()).toContain('3D 顯示中斷')
  expect(wrapper.get('.clinic-model-retry').exists()).toBe(true)
  wrapper.unmount()
})
