import { toScheduleTask } from '@/services/taskApi.js'
import { adaptLiveMapSnapshot, buildLiveMapRoutes } from '@/data/liveMapSnapshot.js'
import { dispatchWaypointLabels } from '@/config/dispatchDestinations.js'
import { robotDisplayCode } from '@/config/robotDisplayCode.js'

const dayKey = date => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
const validDate = value => value && !Number.isNaN(new Date(value).getTime())

export function dashboardSnapshot(robotSnapshot, records, graph, today = new Date()) {
  const { robots, tasks } = adaptLiveMapSnapshot(robotSnapshot, records)
  const routeByRobot = new Map((graph ? buildLiveMapRoutes(graph, tasks) : []).map(route => [route.robotId, route]))
  const vertexById = new Map((graph?.vertices || []).map(vertex => [vertex.id, vertex]))
  const calendarDates = Array.from({ length: 61 }, (_, offset) => {
    const date = new Date(today.getFullYear(), today.getMonth(), today.getDate() + offset - 30)
    const key = dayKey(date)
    return {
      key, day: date.getDate(), month: date.getMonth() + 1, weekday: new Intl.DateTimeFormat('zh-TW', { weekday: 'long' }).format(date), today: key === dayKey(today),
      items: records.filter(record => validDate(record.scheduledAt) && dayKey(new Date(record.scheduledAt)) === key)
        .map(record => {
          const task = toScheduleTask(record)
          return { id: record.id, time: task.startTime.slice(0, 5), title: task.title,
            assignee: record.assignedRobot ? robotDisplayCode(record.assignedRobot) : null,
            assignmentState: record.dispatched ? 'dispatching' : 'pending',
            source: task.source, destination: task.destination,
            route: `${task.source} → ${task.destination}`,
            state: record.status === 'completed' ? 'completed' : record.status === 'running' ? 'active' : 'pending' }
        }).sort((a, b) => a.time.localeCompare(b.time)),
    }
  })
  const todayTasks = records.filter(record => validDate(record.scheduledAt) && dayKey(new Date(record.scheduledAt)) === dayKey(today) && record.status !== 'cancelled')
  const completed = todayTasks.filter(record => record.status === 'completed').length
  const completion = { completed, total: todayTasks.length, percentage: todayTasks.length ? Math.round(completed / todayTasks.length * 100) : null }
  const progressByRobot = Object.fromEntries(robots.map(robot => {
    const record = records.find(task => task.assignedRobot === robot.id && task.status === 'running')
    const route = routeByRobot.get(robot.id)
    const path = route?.vertexIds || []
    const intermediate = path.slice(1,-1).map(id => vertexById.get(id)?.name)
      .filter(name => name && dispatchWaypointLabels[name] && name !== record?.source && name !== record?.destination)
    const stops = [record?.source, ...[...new Set(intermediate)].slice(0, 3), record?.destination].filter(Boolean)
    const current = robot.hasPose && graph?.vertices?.length
      ? graph.vertices.filter(vertex => Number.isFinite(vertex.x) && Number.isFinite(vertex.y))
        .sort((a, b) => Math.hypot(a.x - robot.x, a.y - robot.y) - Math.hypot(b.x - robot.x, b.y - robot.y))[0]
      : null
    const steps = [
      ...(record ? [{ role: 'currentLocation', location: current && Math.hypot(current.x - robot.x, current.y - robot.y) < 2
        ? dispatchWaypointLabels[current.name] || current.name : robot.location || '—', status: 'active' }] : []),
      ...stops.map((name,index) => ({
        role: index === 0 ? 'source' : index === stops.length - 1 ? 'destination' : 'via',
        location: dispatchWaypointLabels[name] || name,
        status: 'pending' })),
    ]
    return [robot.id, { robotId: robot.displayCode, robotState: robot.state, taskId: record?.taskCode || '—', floor: robot.floorId === 'floor1' ? 'F1' : '—',
      steps, emptyMessageKey: record ? 'noRoute' : 'noActiveTask' }]
  }))
  return { robots, tasks, calendarDates, completion, progressByRobot }
}
