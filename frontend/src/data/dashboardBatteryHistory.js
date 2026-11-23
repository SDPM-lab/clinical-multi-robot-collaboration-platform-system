import { robotDisplayIndex } from '@/config/robotDisplayCode.js'

// Display-only fixture for the seven registered F1 robots while history API is unavailable.
// The keys follow the same displayCode mapping used by the dashboard and live map.
const startingPercent = [86, 74, 63, 92, 79, 68, 83]
const hours = ['08:00', '09:00', '10:00', '11:00', '12:00']

const clockTime = timestamp => new Intl.DateTimeFormat('en-GB', {
  hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
}).format(timestamp)

export function hourlyObservedBatteryHistory(rollingHistory, robotIds, previous = {}) {
  return Object.fromEntries(['floor1', 'floor2', 'floor3'].map(floor => {
    const readings = rollingHistory[floor] || {}
    const timestamps = [...new Set(Object.values(readings).flatMap(points => points.map(point => point.timestamp)))]
      .filter(Number.isFinite).sort((a, b) => a - b)
    const hourly = new Map((previous[floor] || []).map(row => [row.hourStart, row]))
    for (const timestamp of timestamps) {
      const hour = new Date(timestamp)
      hour.setMinutes(0, 0, 0)
      const latest = Object.fromEntries(robotIds.map(id => [
        id, readings[id]?.filter(point => point.timestamp <= timestamp).at(-1),
      ]))
      const hourStart = hour.getTime()
      const existing = hourly.get(hourStart)
      const observedTimestamps = Object.fromEntries(robotIds.map(id => [
        id, Math.max(existing?.observedTimestamps[id] ?? -Infinity, latest[id]?.timestamp ?? -Infinity),
      ]))
      hourly.set(hourStart, {
        hourStart,
        time: clockTime(hour),
        batteries: Object.fromEntries(robotIds.map(id => [
          id, latest[id] && latest[id].timestamp >= (existing?.observedTimestamps[id] ?? -Infinity)
            ? latest[id].value : existing?.batteries[id] ?? null,
        ])),
        observedTimes: Object.fromEntries(robotIds.map(id => [id, Number.isFinite(observedTimestamps[id]) ? clockTime(observedTimestamps[id]) : null])),
        observedTimestamps,
      })
    }
    return [floor, [...hourly.values()].sort((a, b) => a.hourStart - b.hourStart).slice(-5)]
  }))
}

export function dashboardBatteryHistory(robots, observedHistory) {
  const registered = robots.filter(robot => robot.floorId === 'floor1').slice(0, 7)
  const observed = observedHistory?.floor1 || []
  if (observed.length) return { floor1: observed, floor2: [], floor3: [], simulated: false }
  const floor1 = registered.length ? hours.map((time, sampleIndex) => ({
    time,
    batteries: Object.fromEntries(registered.map(robot => {
      const robotIndex = robotDisplayIndex(robot.id || robot.displayCode)
      const variationIndex = Math.max(0, robotIndex)
      return [robot.displayCode, Math.max(0, (startingPercent[robotIndex] ?? 75) - sampleIndex * (variationIndex % 3 + 2))]
    })),
  })) : []
  return { floor1, floor2: [], floor3: [], simulated: floor1.length > 0 }
}
