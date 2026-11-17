import { expect, it } from 'vitest'
import { dashboardBatteryHistory } from '@/data/dashboardBatteryHistory.js'

it('shows seven registered F1 robots in aligned simulated history', () => {
  const robots = ['C01','C02','M01','M02','W01','W02','W03'].map(displayCode => ({ displayCode, floorId: 'floor1' })).reverse()
  const history = dashboardBatteryHistory(robots, { floor1: [] })
  expect(history.simulated).toBe(true)
  expect(history.floor1).toHaveLength(5)
  expect(Object.keys(history.floor1[0].batteries).sort()).toEqual(['C01','C02','M01','M02','W01','W02','W03'])
  expect(history.floor1[0].batteries.C01).toBe(86)
  expect(history.floor2).toEqual([])
})

it('uses observed battery readings when telemetry history exists', () => {
  const row = { time: '12:01', batteries: { C01: 51 } }
  expect(dashboardBatteryHistory([{ displayCode: 'C01', floorId: 'floor1' }], { floor1: [row] })).toMatchObject({ simulated: false, floor1: [row] })
})
