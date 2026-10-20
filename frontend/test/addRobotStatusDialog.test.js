import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import AddRobotStatusDialog from '@/components/robot-status/AddRobotStatusDialog.vue'
import { fleetStore } from '@/stores/demoFleetStore.js'
import { registerRobotAsset } from '@/three/robot/robotModelAssets.js'

vi.mock('@/three/robot/robotModelAssets.js', () => ({
  registerRobotAsset: vi.fn(async () => 'uploaded-test'),
  unregisterRobotAsset: vi.fn(),
}))

let wrapper
afterEach(() => { wrapper?.unmount(); vi.restoreAllMocks() })

describe('Robot Status add dialog', () => {
  it('requires a GLB and submits robot details with the imported asset key', async () => {
    wrapper = mount(AddRobotStatusDialog, { attachTo: document.body })
    expect(wrapper.get('[role="dialog"]').text()).toContain('GLB 模型')
    await wrapper.get('form').trigger('submit')
    expect(wrapper.get('[role="alert"]').text()).toContain('GLB')

    const file = new File(['glb'], 'custom-robot.glb', { type: 'model/gltf-binary' })
    const input = wrapper.get('input[type="file"]')
    Object.defineProperty(input.element, 'files', { configurable: true, value: [file] })
    await input.trigger('change')
    const add = vi.spyOn(fleetStore, 'addRobot').mockImplementation(candidate => ({ ok: true, robot: { ...candidate, state: 'offline' } }))
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(registerRobotAsset).toHaveBeenCalledWith(file)
    expect(add).toHaveBeenCalledWith(expect.objectContaining({ id: 'R08', name: 'Robot 08', floorId: 'floor1', modelAssetKey: 'uploaded-test' }))
    expect(wrapper.emitted('created')?.[0]?.[0]).toMatchObject({ id: 'R08', modelAssetKey: 'uploaded-test' })
  })
})
