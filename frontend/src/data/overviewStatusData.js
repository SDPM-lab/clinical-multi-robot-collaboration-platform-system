// Deterministic fallback only; no history endpoint is currently connected.
export const robotIds = ['R01', 'R02', 'R03']
export const normalizeFloor = (value) => {
  const match = /^(?:floor\s*|f|l)?([123])$/i.exec(String(value ?? ''))
  return match ? `floor${match[1]}` : null
}
const hours = ['08:00', '09:00', '10:00', '11:00', '12:00']
const samples = {
  floor1: [[92,75,68],[89,68,61],[86,55,48],[84,42,28],[82,34,18]],
  floor2: [[88,82,76],[85,79,72],[81,74,68],[77,68,64],[73,61,59]],
  floor3: [[81,74,69],[78,70,64],[74,65,60],[70,61,55],[66,57,51]],
}
export const buildingBatteryHistory = Object.fromEntries(Object.entries(samples).map(([floorId, rows]) => [floorId,
  rows.map((values, index) => ({ time: hours[index], batteries: Object.fromEntries(robotIds.map((id, i) => [id, values[i]])) })),
]))
export const fallbackRobotLocations = { R01: 'floor1', R02: 'floor2', R03: 'floor3' }
export const fallbackUpdatedAt = '2026-09-11T12:00:00+08:00'

export function createFloorRobotStatus(robots, tasks = [], demo = false) {
  return Object.fromEntries(['floor1','floor2','floor3'].map((floorId) => [floorId,
    Object.fromEntries(robotIds.map((robotId, index) => {
      const robot = robots.find((entry) => entry.id === robotId)
      const explicitFloor = robot?.floorId ?? robot?.floor ?? robot?.location?.level_name
      const location = normalizeFloor(explicitFloor) || (demo && explicitFloor == null ? fallbackRobotLocations[robotId] : null)
      const present = location === floorId
      const task = tasks.find((entry) => entry.id === robot?.activeTaskId)
      return [robotId, {
        floorId, robotId, name: robot?.name || `Robot 0${index + 1}`,
        battery: present && Number.isFinite(robot?.battery) ? robot.battery : null,
        status: present ? robot?.state || 'unknown' : location ? 'absent' : 'unknown',
        currentTask: present ? task?.title ?? robot?.currentTask ?? null : null,
        taskId: present ? task?.id ?? robot?.activeTaskId ?? null : null,
        pendingTaskCount: present ? robot?.queuedTasks ?? 0 : null,
        updatedAt: robot?.updatedAt ?? robot?.lastHeartbeatAt ?? (demo ? fallbackUpdatedAt : null),
        thumbnailUrl: robot?.thumbnailUrl || '/images/robot-thumbnail.png',
      }]
    })),
  ]))
}
