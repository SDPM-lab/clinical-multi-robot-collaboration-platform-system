import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import ClinicOverviewView from '@/views/ClinicOverviewView.vue'
import TaskProgressTimeline from '@/components/overview/TaskProgressTimeline.vue'
import { overviewDemoData } from '@/data/overviewDemoData.js'
import { taskApi } from '@/services/taskApi.js'

const SceneStub = {
  props: ['activeFloor', 'cameraDebug', 'modelDebug', 'interactionTarget', 'cameraPreset', 'modelPreset'],
  emits: ['update:modelPreset', 'cameraChange', 'cameraPresetChange'],
  template: '<button class="scene-stub" :data-floor="activeFloor" :data-camera-debug="cameraDebug" :data-model-debug="modelDebug" :data-target="interactionTarget" @click="$emit(\'update:modelPreset\', { ...modelPreset, position: { ...modelPreset.position, x: 2 } })" />',
}

describe('clinic overview view', () => {
  it('shows stale backend data and allows retrying the snapshot', async () => {
    vi.spyOn(taskApi, 'getRobotSnapshot')
      .mockRejectedValueOnce(new Error('offline'))
      .mockResolvedValue({ robots: [] })
    vi.spyOn(taskApi, 'getTaskRecords').mockResolvedValue([])
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false }))
    const wrapper = mount(ClinicOverviewView, {
      props: { data: overviewDemoData, theme: 'light' },
      global: { stubs: { ClinicOverviewScene: SceneStub, RobotPreviewStrip: true } },
    })
    await flushPromises()

    expect(wrapper.get('.dashboard-data-status').attributes('data-state')).toBe('stale')
    expect(wrapper.get('.dashboard-data-status').text()).toContain('資料更新失敗')

    await wrapper.get('.dashboard-data-status button').trigger('click')
    await flushPromises()
    expect(wrapper.get('.dashboard-data-status').attributes('data-state')).toBe('fresh')
    expect(wrapper.get('.dashboard-data-status').text()).toContain('資料來源更新於')

    wrapper.unmount()
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('places backend freshness above the daily schedule in the right information rail', async () => {
    const wrapper = mount(ClinicOverviewView, {
      props: { data: overviewDemoData, theme: 'light' },
      global: { stubs: { ClinicOverviewScene: SceneStub, RobotPreviewStrip: true } },
    })
    const rightRail = wrapper.get('.right-information-stack')

    expect(rightRail.element.firstElementChild).toBe(wrapper.get('.dashboard-data-status').element)
    expect(rightRail.element.children[1]).toBe(wrapper.get('.overview-calendar').element)
    expect(wrapper.element.querySelector(':scope > .dashboard-data-status')).toBeNull()

    wrapper.unmount()
  })

  it('keeps floor selection connected and does not show demo task data', async () => {
    const wrapper = mount(ClinicOverviewView, {
      props: { data: overviewDemoData, theme: 'light' },
      global: { stubs: { ClinicOverviewScene: SceneStub, RobotPreviewStrip: true } },
    })

    expect(wrapper.get('.scene-stub').attributes('data-floor')).toBe('all')
    expect(wrapper.get('.task-progress-panel').text()).toContain('任務進度')
    expect(wrapper.get('.task-progress-panel').text()).not.toContain('T001')
    const gauge = wrapper.get('.f1-speed-gauge').element
    expect(wrapper.findAll('.f1-speed-gauge')).toHaveLength(1)
    expect(wrapper.findAll('.completion-panel-content')).toHaveLength(1)
    expect(wrapper.get('.f1-speed-gauge').attributes('aria-label')).toContain('尚無資料')
    expect(wrapper.findAll('.completion-summary > div')).toHaveLength(3)

    const floorTwo = wrapper.get('.clinic-floor-selector [data-floor="2"]')
    await floorTwo.trigger('click')

    expect(wrapper.get('.scene-stub').attributes('data-floor')).toBe('2')
    expect(wrapper.get('.f1-speed-gauge').element).toBe(gauge)
    expect(wrapper.get('.f1-speed-gauge').attributes('aria-label')).toContain('尚無資料')
    expect(wrapper.get('.completion-panel').text()).not.toContain('13 / 18')
    expect(wrapper.findAll('.task-progress-panel li')).toHaveLength(0)

    expect(wrapper.get('.overview-calendar').text()).not.toContain('T014')
    wrapper.unmount()
  })

  it('opens dispatch schedule from the daily schedule View all action', async () => {
    const wrapper = mount(ClinicOverviewView, {
      props: { data: overviewDemoData, theme: 'light' },
      global: { stubs: { ClinicOverviewScene: SceneStub, RobotPreviewStrip: true } },
    })

    await wrapper.get('.overview-calendar header > button').trigger('click')
    expect(wrapper.emitted('open-dispatch')).toEqual([['schedule']])
    wrapper.unmount()
  })

  it('omits the task progress source note while preserving route steps', () => {
    const wrapper = mount(TaskProgressTimeline, {
      props: {
        modelValue: 'robot-a',
        progressByRobot: {
          'robot-a': {
            taskId: 'T001',
            floor: '1F',
            robotId: 'R01',
            steps: [{ location: 'pharmacy', status: 'active', label: 'Source' }],
          },
        },
      },
    })

    expect(wrapper.find('.progress-source-note').exists()).toBe(false)
    expect(wrapper.findAll('.progress-content li')).toHaveLength(1)
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


it('does not show an expand arrow on the completion rate panel', async () => {
 const wrapper = mount(ClinicOverviewView, {
  props: { data: overviewDemoData, theme: 'light' },
  global: { stubs: { ClinicOverviewScene: SceneStub } },
 })
 expect(wrapper.find('.completion-expand').exists()).toBe(false)
 expect(wrapper.find('.completion-header button').exists()).toBe(false)
 expect(wrapper.find('.f1-speed-gauge').exists()).toBe(true)
 expect(wrapper.get('.scene-stub').attributes('data-floor')).toBe('all')
 wrapper.unmount()
})
