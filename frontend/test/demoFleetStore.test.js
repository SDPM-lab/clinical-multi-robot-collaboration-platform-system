import { describe, expect, it } from 'vitest'
import { demoFleetStore, secondsToTime, timeToSeconds } from '../src/stores/demoFleetStore.js'

const futureTask = (overrides = {}) => ({ robotId: 'R04', title: '藥品配送', type: '藥品配送', taskType: 'medication_delivery', source: 'Pharmacy', destination: 'Ward A', date: '2030-01-01', startTime: '08:00:00', durationSeconds: 720, priority: 'normal', ...overrides })

describe('demo fleet store scheduling rules', () => {
  it('uses the five backend task types and rejects incompatible robot types', () => {
    expect(demoFleetStore.validateTask({ ...futureTask(), robotId: 'R01', endTime: '08:12:00' }).ok).toBe(false)
    expect(demoFleetStore.createTask({ ...futureTask(), taskType: 'Inspection' }).ok).toBe(false)
  })

  it('creates a compatible task with the matching capability and can remove it', () => {
    const created = demoFleetStore.createTask(futureTask())
    expect(created.ok).toBe(true)
    expect(created.task.requiredCapabilities).toEqual(['medication_delivery'])
    const robot = demoFleetStore.robots.value.find(entry => entry.id === 'R04')
    expect(robot.queuedTaskIds).toContain(created.task.id)
    expect(demoFleetStore.deleteTask(created.task.id).ok).toBe(true)
    expect(robot.queuedTaskIds).not.toContain(created.task.id)
  })

  it('cannot cancel an assigned or executing task', () => {
    for (const status of ['assigned', 'executing', 'running']) {
      const task = demoFleetStore.tasks.value[0]
      const previous = task.status
      task.status = status
      expect(demoFleetStore.cancelTask(task.id)).toEqual({ ok: false, reason: 'locked' })
      task.status = previous
    }
  })

  it('rejects unknown map stations and accepts known stations', () => {
    expect(demoFleetStore.validateTask({ ...futureTask(), endTime: '08:12:00' }).ok).toBe(true)
    expect(demoFleetStore.validateTask({ ...futureTask({ destination: 'Director' }), endTime: '08:12:00' }).ok).toBe(false)
  })

  it('keeps second precision in time conversion', () => {
    expect(timeToSeconds('10:05:30')).toBe(36330)
    expect(secondsToTime(36330 + 720)).toBe('10:17:30')
  })

  it('requires the waste transport capability for the clean robot task', () => {
    const task = demoFleetStore.tasks.value.find(entry => entry.taskType === 'waste_transport')
    expect(task.requiredCapabilities).toEqual(['waste_transport'])
  })
})
