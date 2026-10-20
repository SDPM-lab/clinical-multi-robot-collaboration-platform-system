import { expect, it } from 'vitest'
import { createHistorySource } from '@/data/scheduleHistorySource.js'
import { demoFleetStore } from '@/stores/demoFleetStore.js'

it('keeps type-aligned demo history when a dated task is only scheduled', () => {
  const source = createHistorySource()
  expect(source.value.events.length).toBeGreaterThan(0)
  expect(source.value.events.every((event) => ['MedicineDelivery','SpecimenDelivery','GeneralDelivery','WasteCollection'].includes(event.taskType))).toBe(true)
  expect(source.value.demo).toBe(true)

  const created = demoFleetStore.createTask({
    robotId: 'R02', title: '檢體配送', type: '檢體配送', taskType: 'SpecimenDelivery',
    origin: 'Pharmacy', destination: 'Laboratory', date: '2026-10-01',
    startTime: '08:00:00', durationSeconds: 720, priority: 'normal', note: '',
  })
  expect(created.ok).toBe(true)
  try {
    expect(source.value.events.some((event) => event.taskId === created.task.id)).toBe(false)
    expect(source.value.events.every((event) => ['completed', 'failed', 'cancelled'].includes(event.status))).toBe(true)
    expect(source.value.demo).toBe(true)
  } finally {
    demoFleetStore.deleteTask(created.task.id)
  }
})
