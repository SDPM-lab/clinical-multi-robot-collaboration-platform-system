const floorIds = ['floor1', 'floor2', 'floor3']
const historyKey = 'medisync-observed-ros-battery-v1'

export function readObservedBatteryHistory() {
  try {
    const stored = JSON.parse(localStorage.getItem(historyKey))
    return Object.fromEntries(floorIds.map(floor => [floor,
      Array.isArray(stored?.[floor]) ? stored[floor].filter(row =>
        Number.isFinite(row?.hourStart) && row.batteries && row.observedTimestamps).slice(-5) : [],
    ]))
  } catch {
    return {}
  }
}

export function saveObservedBatteryHistory(history) {
  try {
    localStorage.setItem(historyKey, JSON.stringify(history))
  } catch {
    // History remains available in memory when browser storage is disabled.
  }
}

const clockTime = timestamp => new Intl.DateTimeFormat('en-GB', {
  hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
}).format(timestamp)

export function hourlyObservedBatteryHistory(rollingHistory, robotIds, previous = {}) {
  return Object.fromEntries(floorIds.map(floor => {
    const readings = rollingHistory[floor] || {}
    const timestamps = [...new Set(Object.values(readings).flatMap(points => points.map(point => point.timestamp)))]
      .filter(Number.isFinite).sort((a, b) => a - b)
    const hourly = new Map((previous[floor] || []).map(row => [row.hourStart, row]))
    for (const timestamp of timestamps) {
      const hour = new Date(timestamp)
      hour.setMinutes(0, 0, 0)
      const hourStart = hour.getTime()
      const latest = Object.fromEntries(robotIds.map(id => [
        id, readings[id]?.filter(point => point.timestamp >= hourStart && point.timestamp <= timestamp).at(-1),
      ]))
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
