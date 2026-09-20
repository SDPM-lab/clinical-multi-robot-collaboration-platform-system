import { mount } from '@vue/test-utils'
import { expect, it } from 'vitest'
import TaskProgressTimeline from '@/components/overview/TaskProgressTimeline.vue'
import { taskProgressByRobot } from '@/data/clinicOverviewData.js'

it('replaces the timeline only when the robot or task identity changes', async () => {
  const data = structuredClone(taskProgressByRobot)
  const wrapper = mount(TaskProgressTimeline, { props: { modelValue: 'robot01', progressByRobot: data } })
  const first = wrapper.get('ol').element
  data.robot01.steps[0].time = '09:31'
  await wrapper.setProps({ progressByRobot: structuredClone(data) })
  expect(wrapper.get('ol').element).toBe(first)
  expect(wrapper.text()).toContain('09:31')
  data.robot01.taskId = 'T099'
  await wrapper.setProps({ progressByRobot: structuredClone(data) })
  const nextTask = wrapper.get('ol').element
  expect(nextTask).not.toBe(first)
  await wrapper.setProps({ modelValue: 'robot02' })
  expect(wrapper.get('ol').element).not.toBe(nextTask)
  expect(wrapper.text()).toContain('T014')
  wrapper.unmount()
})

it('renders the active delivery with a simple pulse marker instead of an icon', () => {
  const wrapper = mount(TaskProgressTimeline, { props: { modelValue: 'robot01', progressByRobot: taskProgressByRobot } })
  const activeStep = wrapper.get('li.is-active')
  expect(activeStep.text()).toContain('配送')
  expect(activeStep.find('.active-pulse-dot').exists()).toBe(true)
  expect(activeStep.find('.timeline-node svg').exists()).toBe(false)
  wrapper.unmount()
})
