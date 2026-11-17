import { robotDisplayIndex } from '@/config/robotDisplayCode.js'

// Display-only fixture for the seven registered F1 robots while history API is unavailable.
// The keys follow the same displayCode mapping used by the dashboard and live map.
const startingPercent = [86, 74, 63, 92, 79, 68, 83]
const hours = ['08:00', '09:00', '10:00', '11:00', '12:00']

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
