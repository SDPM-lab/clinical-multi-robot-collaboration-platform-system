import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import TaskGantt from '../src/components/dispatch/TaskGantt.vue'
import {
  getAnchoredScrollLeft,
  getDragSnapSeconds,
  getNextZoom,
  hasTimelineConflict,
  normalizePriority,
  priorityBubbleSize,
  shiftIsoDate,
  snapTaskStart,
} from '../src/components/dispatch/taskTimeline.js'

describe('dispatch timeline interactions', () => {
  it('uses three practical zoom ranges', () => {
    expect(getNextZoom(1, 1)).toBe(2)
    expect(getNextZoom(2, 1)).toBe(5)
    expect(getNextZoom(5, -1)).toBe(2)
  })

  it('starts locked, opens details on click, and only enables drag styling in edit mode', async () => {
    globalThis.ResizeObserver = class { observe() {} disconnect() {} }
    const wrapper = mount(TaskGantt, {
      props: {
        date: '2026-08-31',
        robots: [
          { id: 'R01', name: 'Robot 01', battery: 82, state: 'executing' },
          { id: 'R02', name: 'Robot 02', battery: 34, state: 'charging' },
          { id: 'R03', name: 'Robot 03', battery: 18, state: 'idle' },
        ],
        tasks: [{ id: 'T001', robotId: 'R01', title: '藥品配送', origin: 'Pharmacy', destination: 'Nurse Reception', priority: 'high', status: 'executing', startTime: '09:30:00', endTime: '09:42:00', durationSeconds: 720 }],
      },
    })
    expect(wrapper.find('.timeline-grid').classes()).not.toContain('is-editing')
    expect(wrapper.find('.timeline-legend').text()).toContain('Robot 01')
    expect(wrapper.find('.task-bubble').text()).toContain('T001')
    expect(wrapper.find('.task-duration-range').exists()).toBe(true)
    expect(wrapper.find('.task-bar').exists()).toBe(false)
    expect(wrapper.find('.timeline-axis time').text()).toMatch(/\d{2}:\d{2}:\d{2}/)
    expect(wrapper.findAll('button').some((button) => button.attributes('aria-label') === '放大時間軸')).toBe(false)
    await wrapper.find('.task-bubble').trigger('pointerdown')
    expect(wrapper.find('.task-detail-popover').exists()).toBe(true)
    const edit = wrapper.findAll('button').find((button) => button.text() === '編輯排程')
    await edit.trigger('click')
    expect(wrapper.find('.timeline-grid').classes()).toContain('is-editing')
    const cancel = wrapper.findAll('button').find((button) => button.text() === '取消')
    await cancel.trigger('click')
    expect(wrapper.find('.timeline-grid').classes()).not.toContain('is-editing')
  })

  it('zooms from wheel input registered on the timeline viewport', async () => {
    globalThis.ResizeObserver = class { observe() {} disconnect() {} }
    const wrapper = mount(TaskGantt, {
      props: {
        date: '2026-08-31',
        robots: [
          { id: 'R01', name: 'Robot 01', battery: 82, state: 'executing' },
          { id: 'R02', name: 'Robot 02', battery: 34, state: 'charging' },
          { id: 'R03', name: 'Robot 03', battery: 18, state: 'idle' },
        ],
        tasks: [],
      },
    })
    const viewport = wrapper.find('.time-viewport').element
    viewport.getBoundingClientRect = () => ({ left: 0, width: 900 })
    expect(wrapper.find('.time-canvas').attributes('style')).toContain('1800px')
    viewport.dispatchEvent(new WheelEvent('wheel', { deltaY: -100, clientX: 450, bubbles: true, cancelable: true }))
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.time-canvas').attributes('style')).toContain('2016')
    wrapper.unmount()
  })

  it('keeps the time under the cursor anchored while zooming', () => {
    const next = getAnchoredScrollLeft({ oldZoom: 1, newZoom: 2, viewportWidth: 1000, scrollLeft: 0, cursorX: 250 })
    expect(next).toBe(250)
    expect((next + 250) / 2000).toBe((0 + 250) / 1000)
  })

  it('uses zoom-aware 5-minute, 1-minute, and 10-second drag snapping', () => {
    expect(getDragSnapSeconds(4)).toBe(300)
    expect(getDragSnapSeconds(15)).toBe(60)
    expect(getDragSnapSeconds(26)).toBe(10)
    expect(snapTaskStart(9 * 3600 + 77, 720, 300)).toBe(9 * 3600)
    expect(snapTaskStart(9 * 3600 + 77, 720, 60)).toBe(9 * 3600 + 60)
    expect(snapTaskStart(9 * 3600 + 77, 720, 10)).toBe(9 * 3600 + 80)
  })

  it('maps priorities to exactly three bubble sizes', () => {
    expect(priorityBubbleSize).toEqual({ low: 34, normal: 46, high: 60 })
    expect(normalizePriority(90)).toBe('high')
    expect(normalizePriority(50)).toBe('normal')
    expect(normalizePriority(10)).toBe('low')
  })

  it('detects same-robot draft overlaps before save', () => {
    const task = { id: 'T001', robotId: 'R01', title: '藥品配送', durationSeconds: 720 }
    const tasks = [task, { id: 'T003', robotId: 'R01', title: '巡檢', startTime: '10:00:00', durationSeconds: 600 }]
    const robots = [{ id: 'R01', state: 'idle', battery: 82 }]
    expect(hasTimelineConflict({ task, startSeconds: 10 * 3600 + 60, drafts: {}, tasks, robots })).toContain('時間重疊')
  })

  it('changes calendar dates without timezone drift', () => {
    expect(shiftIsoDate('2026-08-31', -1)).toBe('2026-08-30')
    expect(shiftIsoDate('2026-08-31', 1)).toBe('2026-09-01')
  })
})
