import { expect, it } from 'vitest'
import { dashboardBatteryHistory, hourlyObservedBatteryHistory } from '@/data/dashboardBatteryHistory.js'

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

it('groups readings by local hour and retains each robot’s latest actual reading time', () => {
  const at = (hour, minute) => new Date(2026, 10, 20, hour, minute).getTime()
  const history = hourlyObservedBatteryHistory({
    floor1: {
      C01: [{ timestamp: at(13, 1), value: 80 }, { timestamp: at(13, 41), value: 79 }, { timestamp: at(14, 3), value: 78 }],
      C02: [{ timestamp: at(13, 20), value: 65 }],
    },
  }, ['C01', 'C02'])
  expect(history.floor1).toEqual([
    { hourStart: at(13, 0), time: '13:00', batteries: { C01: 79, C02: 65 }, observedTimes: { C01: '13:41', C02: '13:20' }, observedTimestamps: { C01: at(13, 41), C02: at(13, 20) } },
    { hourStart: at(14, 0), time: '14:00', batteries: { C01: 78, C02: 65 }, observedTimes: { C01: '14:03', C02: '13:20' }, observedTimestamps: { C01: at(14, 3), C02: at(13, 20) } },
  ])
  expect(history.floor2).toEqual([])
  const later = hourlyObservedBatteryHistory({
    floor1: { C01: [{ timestamp: at(15, 2), value: 77 }] },
  }, ['C01', 'C02'], history)
  expect(later.floor1.map(row => row.time)).toEqual(['13:00', '14:00', '15:00'])
  expect(later.floor1[0].batteries.C01).toBe(79)
  const trimmed = hourlyObservedBatteryHistory({
    floor1: { C01: [{ timestamp: at(13, 41), value: 79 }] },
  }, ['C01', 'C02'], history)
  expect(trimmed.floor1[0].batteries.C02).toBe(65)
})
