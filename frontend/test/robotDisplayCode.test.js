import { describe, expect, it } from 'vitest'
import { robotDisplayCode, robotDisplayCodes, robotDisplayIndex } from '@/config/robotDisplayCode.js'

describe('robot display codes', () => {
  it('uses the type prefix and per-type sequence for the seven configured robots', () => {
    expect(robotDisplayCodes).toEqual(['C01', 'C02', 'M01', 'M02', 'W01', 'W02', 'W03'])
    expect(['R01', 'R02', 'R03', 'R04', 'R05', 'R06', 'R07'].map(robotDisplayCode)).toEqual(robotDisplayCodes)
  })

  it('maps backend robot identifiers without changing unknown identifiers', () => {
    expect(['robot-a', 'robot-b'].map(robotDisplayCode)).toEqual(robotDisplayCodes.slice(0, 2))
    expect(Array.from({ length: 7 }, (_, index) => `robot-hospital_robot_${index + 1}`).map(robotDisplayCode))
      .toEqual(robotDisplayCodes)
    expect(robotDisplayCode('/hospital_robot_3')).toBe('M01')
    expect(robotDisplayCode('new-robot')).toBe('new-robot')
    expect(robotDisplayIndex('robot-hospital_robot_6')).toBe(5)
  })
})
