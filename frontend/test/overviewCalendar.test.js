import { mount } from '@vue/test-utils'
import { expect, it } from 'vitest'
import OverviewCalendar from '@/components/overview/OverviewCalendar.vue'

it('places the task status dot before its time in the schedule list', () => {
  const wrapper = mount(OverviewCalendar, {
    props: {
      modelValue: '2026-11-09',
      dates: [{
        key: '2026-11-09',
        month: 11,
        day: 9,
        weekday: '星期一',
        items: [{
          id: 'task-1',
          time: '22:03',
          title: '藥品配送',
          source: '藥局',
          destination: '病房 A',
          assignee: 'M01',
          state: 'active',
          route: '藥局 → 病房 A',
        }],
      }],
    },
  })

  const item = wrapper.get('.schedule-list li')
  expect(Array.from(item.element.children).slice(0, 3).map(child => child.tagName)).toEqual(['I', 'TIME', 'DIV'])
  wrapper.unmount()
})
