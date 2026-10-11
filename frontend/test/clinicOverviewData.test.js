import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { clinicOverviewModelUrl, completionByFloor, createClinicDailySchedules, taskProgressByRobot } from '@/data/clinicOverviewData.js'

describe('clinic overview dashboard data', () => {
  it('uses the current GLB asset revision', () => {
    const bytes = readFileSync('public/models/hospital_overview.glb')
    const revision = createHash('sha256').update(bytes).digest('hex').slice(0, 8)
    expect(clinicOverviewModelUrl).toBe('/models/hospital_overview.glb?v=' + revision)
  })
  it('keeps distinct completion values for the building and each floor', () => {
    expect(completionByFloor.all.map(({ percentage }) => percentage)).toEqual([86, 72, 64])
    expect(completionByFloor['1']).toMatchObject({ completed: 18, total: 21, percentage: 86 })
    expect(completionByFloor['2']).toMatchObject({ completed: 13, total: 18, percentage: 72 })
    expect(completionByFloor['3']).toMatchObject({ completed: 9, total: 14, percentage: 64 })
  })

  it('provides distinct human-readable progress for all three robots', () => {
    expect(Object.keys(taskProgressByRobot)).toEqual(['robot01', 'robot02', 'robot03'])
    expect(new Set(Object.values(taskProgressByRobot).map(({ taskId }) => taskId)).size).toBe(3)
    expect(JSON.stringify(taskProgressByRobot)).not.toContain('_junction')
  })

  it('builds a nine-day schedule centered on the selected day', () => {
    const schedules = createClinicDailySchedules(new Date(2026, 8, 9))
    expect(schedules.map(({ day }) => day)).toEqual([5, 6, 7, 8, 9, 10, 11, 12, 13])
    expect(schedules[4]).toMatchObject({ month: 9, day: 9, weekday: '星期三', today: true })
    expect(schedules[4].items.length).toBeGreaterThan(0)
    expect(completionByFloor.all.every(({ color }) => !['#4b9c91', '#55a873'].includes(color))).toBe(true)
  })
})
