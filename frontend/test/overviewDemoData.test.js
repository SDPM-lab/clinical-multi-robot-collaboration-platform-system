import { describe, expect, it } from 'vitest'

import {
  getAverageBattery,
  getTaskCompletion,
  overviewDemoData,
} from '@/data/overviewDemoData.js'

describe('overview demo data derivations', () => {
  it('derives completion instead of storing it separately', () => {
    expect(getTaskCompletion(overviewDemoData.tasks)).toBe(86)
  })

  it('derives average battery from robot values', () => {
    expect(getAverageBattery(overviewDemoData.robots)).toBe(45)
  })

  it('handles empty source collections safely', () => {
    expect(getTaskCompletion({ completed: 0, inProgress: 0, waiting: 0 })).toBe(0)
    expect(getAverageBattery([])).toBe(0)
  })
})
