import { visualTokens, colorHex } from '@/config/visualTokens.js'
import { timeToSeconds } from '@/stores/demoFleetStore.js'
import { fallbackRobotVisualTheme, getRobotVisualTheme, robotVisualThemes } from '@/config/robotVisualThemes.js'

export const robotRouteColors = Object.freeze({
  ...Object.fromEntries(Object.entries(robotVisualThemes).map(([id, theme]) => [id, Object.freeze({
    main: theme.mainHex,
    completed: theme.completedHex,
    arrow: theme.glowHex,
  })])),
  R04: Object.freeze({ main: fallbackRobotVisualTheme.mainHex, completed: fallbackRobotVisualTheme.completedHex, arrow: fallbackRobotVisualTheme.glowHex }),
  R05: Object.freeze({ main: fallbackRobotVisualTheme.mainHex, completed: fallbackRobotVisualTheme.completedHex, arrow: fallbackRobotVisualTheme.glowHex }),
})
export const overviewRouteColors = Object.freeze({ pending: colorHex(visualTokens.primary), completed: colorHex(visualTokens.primary), arrow: colorHex(visualTokens.primary) })
export const routeVisualConfig = Object.freeze({
  baseRouteRadius: 0.04,
  width: 0.32,
  activeRouteRadius: 0.16,
  selectedRouteRadius: 0.192,
  opacity: 0.82,
  arrowLength: 0.42,
  arrowWidth: 0.34,
  arrowSpacing: 1.15,
  arrowFlowSpeed: 0.9,
  baseHeight: 0.025,
  routeHeight: 0.055,
  completedHeight: 0.065,
  arrowHeight: 0.085,
})
export const routeLayerY = Object.freeze({ R01: 0.031, R02: 0.034, R03: 0.037 })
export const priorityOrder = Object.freeze({ emergency: 0, high: 1, normal: 2, low: 3 })

export const sortTasksByPriority = (tasks) => [...tasks].sort((first, second) => (
  (priorityOrder[first.priority] ?? priorityOrder.normal) - (priorityOrder[second.priority] ?? priorityOrder.normal)
  || timeToSeconds(first.startTime) - timeToSeconds(second.startTime)
  || first.id.localeCompare(second.id)
))

const baseLocationDetails = Object.freeze({
  reception_back: { label: 'Nurse Reception' }, nurse_station: { label: 'Nurse Station' },
  pharmacy: { label: 'Pharmacy' }, consult_2_1: { label: 'Consultation Room 2' },
  ward_a_1: { label: 'Ward A' }, charging_station_1: { label: 'Charging Station A', statusKey: 'charging' },
  charging_station_2: { label: 'Charging Station B', statusKey: 'charging' },
  lab: { label: 'Laboratory' }, pantry: { label: 'Pantry' },
})
export const locationDetails = baseLocationDetails
export const demoRobotWaypoints = Object.freeze({ R02: 'consult_2_1', R03: 'nurse_station' })

export const shortestVertexPath = (data, from, to) => {
  const adjacency = new Map(data.vertices.map((vertex) => [vertex.id, []]))
  data.lanes.forEach((lane) => adjacency.get(lane.from)?.push(lane.to))
  const queue = [[from]]; const visited = new Set([from])
  while (queue.length) {
    const path = queue.shift(); const current = path.at(-1)
    if (current === to) return path
    for (const neighbor of adjacency.get(current) || []) {
      if (visited.has(neighbor)) continue
      visited.add(neighbor); queue.push([...path, neighbor])
    }
  }
  return []
}

export const buildActiveRoutes = (data, tasks) => {
  const byLabel = new Map(data.namedWaypoints.filter((waypoint) => baseLocationDetails[waypoint.name]).map((waypoint) => [baseLocationDetails[waypoint.name].label, waypoint]))
  const progressByRobot = { R01: 0.42, R02: 0.18, R03: 0.3 }
  return sortTasksByPriority(tasks.filter((task) => task.status === 'executing')).map((task) => {
    const direction = task.direction || 'outbound'
    const routeOrigin = byLabel.get(direction === 'return' ? task.destination : task.origin)
    const routeDestination = byLabel.get(direction === 'return' ? task.origin : task.destination)
    return { ...task, taskId: task.id, direction, vertexIds: routeOrigin && routeDestination ? shortestVertexPath(data, routeOrigin.id, routeDestination.id) : [], progress: progressByRobot[task.robotId] ?? 0, colors: robotRouteColors[task.robotId] || robotRouteColors.R04 }
  }).filter((route) => route.vertexIds.length > 1)
}

export const buildLocationDetails = (tasks) => {
  const details = Object.fromEntries(Object.entries(baseLocationDetails).map(([key, value]) => [key, { ...value }]))
  const keyByLabel = new Map(Object.entries(details).map(([key, value]) => [value.label, key]))
  sortTasksByPriority(tasks.filter((task) => task.status === 'executing' || task.status === 'arrived')).forEach((task) => {
    const activeDestination = task.direction === 'return' ? task.origin : task.destination
    for (const label of [task.origin, task.destination]) {
      const key = keyByLabel.get(label)
      if (!key || details[key].taskId) continue
      const theme = getRobotVisualTheme(task.robotId)
      details[key] = {
        ...details[key],
        taskId: task.id,
        robot: `Robot ${task.robotId.slice(1)}`,
        robotId: task.robotId,
        priority: task.priority,
        statusKey: 'active',
        color: theme.mainHex,
        theme,
        isDestination: label === activeDestination,
      }
    }
  })
  return details
}

export const demoActiveRoutes = Object.freeze([])
