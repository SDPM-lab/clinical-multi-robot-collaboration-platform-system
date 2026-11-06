import { describe, expect, it } from 'vitest'

import { overviewDemoData } from '@/data/overviewDemoData.js'
import {
  getBatteryColor,
  robotStateColors,
  robotStateLabels,
} from '@/data/robotStatus.js'

describe('overview robot operational status', () => {
  it('keeps work state separate from low battery status', () => {
    const robot = overviewDemoData.robots.find(({ id }) => id === 'R03')

    expect(robotStateLabels[robot.state]).toBe('待命')
    expect(robot.battery).toBe(18)
    expect(getBatteryColor(robot.battery)).toBe('#C96561')
  })

  it('uses the requested muted status colors', () => {
    expect(robotStateColors).toEqual({
      idle: '#6F9B7B',
      busy: '#C96F3B',
      charging: '#4F9F91',
      offline: '#898E8B',
      error: '#C96561',
    })
  })

  it('maps battery thresholds independently', () => {
    expect(getBatteryColor(20)).toBe('#C96561')
    expect(getBatteryColor(21)).toBe('#C59A52')
    expect(getBatteryColor(40)).toBe('#C59A52')
    expect(getBatteryColor(41)).toBe('#6F9B7B')
  })
})
