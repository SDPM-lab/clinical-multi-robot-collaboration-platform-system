import { expect, it } from 'vitest'
import { hourlyObservedBatteryHistory, readObservedBatteryHistory, saveObservedBatteryHistory } from '@/data/dashboardBatteryHistory.js'

it('shows no readings until real telemetry exists', () => {
  expect(hourlyObservedBatteryHistory({}, ['C01'])).toEqual({ floor1: [], floor2: [], floor3: [] })
})

it('keeps recorded values after a reload and an empty disconnected snapshot', () => {
  const timestamp = new Date(2026, 10, 20, 12, 1).getTime()
  const history = hourlyObservedBatteryHistory({ floor1: { C01: [{ timestamp, value: 51 }] } }, ['C01'])
  saveObservedBatteryHistory(history)
  const saved = readObservedBatteryHistory()
  expect(hourlyObservedBatteryHistory({}, ['C01'], saved)).toEqual(history)
  localStorage.clear()
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
    { hourStart: at(14, 0), time: '14:00', batteries: { C01: 78, C02: null }, observedTimes: { C01: '14:03', C02: null }, observedTimestamps: { C01: at(14, 3), C02: -Infinity } },
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
