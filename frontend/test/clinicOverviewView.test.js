import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ClinicOverviewView from '@/views/ClinicOverviewView.vue'
import { overviewDemoData } from '@/data/overviewDemoData.js'

const SceneStub = {
  props: ['activeFloor', 'cameraDebug', 'modelDebug', 'interactionTarget', 'cameraPreset', 'modelPreset'],
  emits: ['update:modelPreset', 'cameraChange', 'cameraPresetChange'],
  template: '<button class="scene-stub" :data-floor="activeFloor" :data-camera-debug="cameraDebug" :data-model-debug="modelDebug" :data-target="interactionTarget" @click="$emit(\'update:modelPreset\', { ...modelPreset, position: { ...modelPreset.position, x: 2 } })" />',
}

describe('clinic overview view', () => {
  it('keeps floor selection connected to the scene and shows vertical task progress', async () => {
    const wrapper = mount(ClinicOverviewView, {
      props: { data: overviewDemoData, theme: 'light' },
      global: { stubs: { ClinicOverviewScene: SceneStub, RobotPreviewStrip: true } },
    })

    expect(wrapper.get('.scene-stub').attributes('data-floor')).toBe('all')
    expect(wrapper.get('.task-progress-panel').text()).toContain('任務進度')
    expect(wrapper.get('.task-progress-panel').text()).toContain('T001')
    const gauge = wrapper.get('.f1-speed-gauge').element
    expect(wrapper.findAll('.f1-speed-gauge')).toHaveLength(1)
    expect(wrapper.findAll('.completion-panel-content')).toHaveLength(1)
    expect(wrapper.get('.f1-speed-gauge').attributes('aria-label')).toContain('75%')
    expect(wrapper.findAll('.completion-summary > div')).toHaveLength(3)

    const floorTwo = wrapper.findAll('.clinic-floor-selector button').find((button) => button.text().includes('Floor 2'))
    await floorTwo.trigger('click')

    expect(wrapper.get('.scene-stub').attributes('data-floor')).toBe('2')
    expect(wrapper.get('.f1-speed-gauge').element).toBe(gauge)
    expect(wrapper.get('.f1-speed-gauge').attributes('aria-label')).toContain('72%')
    expect(wrapper.get('.completion-panel').text()).toContain('13 / 18')
    expect(wrapper.findAll('.task-progress-panel li')).toHaveLength(4)

    await wrapper.findAll('.overview-calendar nav button')[1].trigger('click')
    expect(wrapper.findAll('.overview-calendar nav button')).toHaveLength(7)
    expect(wrapper.get('.overview-calendar header').text()).toContain('星期')

    await wrapper.get('.robot-select > button').trigger('click')
    await wrapper.findAll('.robot-options button')[1].trigger('click')
    expect(wrapper.get('.task-progress-panel').text()).toContain('T014')
    wrapper.unmount()
  })

  it('only exposes model controls through the modelDebug query', async () => {
    window.history.pushState({}, '', '/?modelDebug=1')
    const wrapper = mount(ClinicOverviewView, {
      props: { data: overviewDemoData, theme: 'light' },
      global: { stubs: { ClinicOverviewScene: SceneStub, RobotPreviewStrip: true } },
    })
    expect(wrapper.get('.scene-stub').attributes('data-model-debug')).toBe('true')
    expect(wrapper.get('.overview-debug-panel').exists()).toBe(true)
    await wrapper.get('.scene-stub').trigger('click')
    expect(wrapper.get('.overview-debug-panel').text()).toContain('Reset model')
    wrapper.unmount()
    window.history.pushState({}, '', '/')
    localStorage.removeItem('overview-model-preset-v4')
  })

  it('lets combined debug mode switch between independent camera and model controls', async () => {
    window.history.pushState({}, '', '/?cameraDebug=1&modelDebug=1')
    const wrapper = mount(ClinicOverviewView, {
      props: { data: overviewDemoData, theme: 'light' },
      global: { stubs: { ClinicOverviewScene: SceneStub, RobotPreviewStrip: true } },
    })
    expect(wrapper.get('.scene-stub').attributes('data-target')).toBe('camera')
    await wrapper.findAll('.debug-target-switch button')[1].trigger('click')
    expect(wrapper.get('.scene-stub').attributes('data-target')).toBe('model')
    wrapper.unmount()
    window.history.pushState({}, '', '/')
  })
})
