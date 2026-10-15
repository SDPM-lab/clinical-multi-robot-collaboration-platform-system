import { computed, reactive, readonly } from 'vue'
import { dispatchTaskLocations } from '@/config/dispatchDestinations.js'

export const ROBOT_CAPABILITY_OPTIONS = Object.freeze([
  '藥品配送', '檢體運送', '物資補充', '醫療廢棄物運送', '文件配送',
  '巡檢', '自動充電', '門控制', '電梯',
])

export const ROBOT_NAV_GRAPHS = Object.freeze([
  Object.freeze({ index: 0, label: 'Graph 0・機器人導航路網' }),
])

export const GRAPH_0_CHARGING_WAYPOINTS = Object.freeze(['charging_station_1'])

const commonRobot = Object.freeze({
  model: 'Hospital AMR',
  floorId: null,
  motorTemperature: null,
  temperatureSource: 'unavailable',
  chargingCommand: null,
  manufacturer: null,
  serialNumber: null,
  thumbnailUrl: '/images/robot-thumbnail.png',
  fleetName: 'hospital_fleet',
  fleetAdapter: 'rmf_demos_fleet_adapter',
  rosDomainId: null,
  connectionEndpoint: null,
  navGraphIndex: 0,
  connectionState: 'disconnected',
  batteryCapacityWh: 960,
  batteryHealth: null,
  minimumTaskBattery: 20,
  rechargeThreshold: 10,
  maxPayloadKg: null,
  maxSpeedMps: 0.7,
  footprintRadiusM: 0.35,
  chargingWaypoint: 'charging_station_1',
  capabilities: Object.freeze(['藥品配送', '檢體運送', '物資補充', '文件配送', '巡檢', '自動充電']),
  completedTaskIds: Object.freeze([]),
  firmwareVersion: null,
  estimatedAvailableTime: null,
  lastHeartbeatAt: null,
  localizationState: null,
  navigationState: null,
  warnings: Object.freeze([]),
})

const makeRobot = (robot) => ({
  ...commonRobot,
  ...robot,
  capabilities: [...(robot.capabilities || commonRobot.capabilities)],
  queuedTaskIds: [...(robot.queuedTaskIds || [])],
  completedTaskIds: [...(robot.completedTaskIds || [])],
  warnings: [...(robot.warnings || [])],
})

const initialRobots = [
  makeRobot({ motorTemperature: 48, temperatureSource: 'demo', id: 'R01', name: 'Robot 01', floorId: 'floor1', rosNamespace: '/robot_01', battery: 82, state: 'executing', currentLocation: 'Nurse Reception', currentWaypoint: 'reception_back', activeTaskId: 'T001', queuedTaskIds: [], queuedTasks: 0 }),
  makeRobot({ motorTemperature: 61, temperatureSource: 'demo', id: 'R02', name: 'Robot 02', floorId: 'floor2', rosNamespace: '/robot_02', battery: 34, state: 'executing', currentLocation: 'Consultation Room 2', currentWaypoint: 'consult_2_1', activeTaskId: 'T002', queuedTaskIds: [], queuedTasks: 0 }),
  makeRobot({ motorTemperature: 73, temperatureSource: 'demo', id: 'R03', name: 'Robot 03', floorId: 'floor3', rosNamespace: '/robot_03', battery: 18, state: 'executing', currentLocation: 'Nurse Station', currentWaypoint: 'nurse_station', activeTaskId: 'T003', queuedTaskIds: ['T006', 'T009'], queuedTasks: 2 }),
]

const initialTasks = [
  { id: 'T001', robotId: 'R01', title: '藥品配送', origin: 'Pharmacy', destination: 'Nurse Reception', priority: 'high', startTime: '09:30:00', endTime: '09:42:00', durationSeconds: 720, status: 'executing', direction: 'outbound', progress: 42 },
  { id: 'T002', robotId: 'R02', title: '檢體運送', origin: 'Consultation Room 2', destination: 'Pantry', priority: 'normal', startTime: '11:00:00', endTime: '11:18:00', durationSeconds: 1080, status: 'executing', direction: 'outbound', progress: 18 },
  { id: 'T003', robotId: 'R03', title: '病房物資補充', origin: 'Nurse Station', destination: 'Ward A', priority: 'high', startTime: '14:20:00', endTime: '14:38:00', durationSeconds: 1080, status: 'executing', direction: 'outbound', progress: 30 },
  { id: 'T006', robotId: 'R03', title: '前往充電', origin: 'Ward A', destination: 'Charging Station A', priority: 'normal', startTime: '16:00:00', endTime: '16:15:00', durationSeconds: 900, status: 'scheduled' },
  { id: 'T009', robotId: 'R03', title: '文件配送', origin: 'Nurse Station', destination: 'Nurse Reception', priority: 'low', startTime: '17:00:00', endTime: '17:12:00', durationSeconds: 720, status: 'scheduled' },
]

export const timeToSeconds = (value) => {
  const [hours = 0, minutes = 0, seconds = 0] = String(value).split(':').map(Number)
  return hours * 3600 + minutes * 60 + seconds
}

export const secondsToTime = (value) => {
  const seconds = ((Math.round(value) % 86400) + 86400) % 86400
  return [Math.floor(seconds / 3600), Math.floor((seconds % 3600) / 60), seconds % 60].map((part) => String(part).padStart(2, '0')).join(':')
}

const state = reactive({
  robots: initialRobots.map(makeRobot),
  tasks: initialTasks.map((task) => ({ ...task })),
  notification: '',
})

const reachableLocations = new Set(dispatchTaskLocations)

const normalizeRosNamespace = (value) => {
  const normalized = String(value || '').trim().replace(/^\/+|\/+$/g, '')
  return normalized ? `/${normalized}` : ''
}

const validateTask = (candidate, ignoreId = null) => {
  const robot = state.robots.find((entry) => entry.id === candidate.robotId)
  if (!robot) return { ok: false, reason: '找不到指定機器人。' }
  if (robot.state === 'offline') return { ok: false, reason: '機器人目前離線。' }
  if (robot.battery < 20 && candidate.title !== '前往充電') return { ok: false, reason: '機器人電量不足 20%。' }
  if (!reachableLocations.has(candidate.origin) || !reachableLocations.has(candidate.destination)) return { ok: false, reason: '請選擇 RMF 路網中可達的起點與目的地。' }
  const start = timeToSeconds(candidate.startTime)
  const end = timeToSeconds(candidate.endTime)
  const sameDate = (task) => (task.date || '2026-08-31') === (candidate.date || '2026-08-31')
  const chargingConflict = state.tasks.find((task) => task.robotId === candidate.robotId && task.id !== ignoreId && sameDate(task) && task.title === '前往充電' && start < timeToSeconds(task.endTime) && end > timeToSeconds(task.startTime))
  if (chargingConflict) return { ok: false, reason: '與充電時段衝突。' }
  const overlap = state.tasks.find((task) => task.robotId === candidate.robotId && task.id !== ignoreId && sameDate(task) && start < timeToSeconds(task.endTime) && end > timeToSeconds(task.startTime))
  if (overlap) return { ok: false, reason: `與 ${overlap.id}「${overlap.title}」時間重疊。` }
  return { ok: true }
}

const moveTask = (taskId, startSeconds, { force = false } = {}) => {
  const task = state.tasks.find((entry) => entry.id === taskId)
  if (!task) return { ok: false, reason: '找不到任務。' }
  const duration = task.durationSeconds
  const candidate = { ...task, startTime: secondsToTime(startSeconds), endTime: secondsToTime(startSeconds + duration) }
  const result = validateTask(candidate, task.id)
  if (!result.ok && !force) return result
  Object.assign(task, candidate)
  return { ok: true, task }
}

const moveTasks = (changes) => {
  const planned = state.tasks.map((task) => ({ ...task }))
  for (const change of changes) {
    const task = planned.find((entry) => entry.id === change.taskId)
    if (!task) return { ok: false, taskId: change.taskId, reason: '找不到任務。' }
    task.startTime = secondsToTime(change.startSeconds)
    task.endTime = secondsToTime(change.startSeconds + task.durationSeconds)
  }
  for (const change of changes) {
    const task = planned.find((entry) => entry.id === change.taskId)
    const robot = state.robots.find((entry) => entry.id === task.robotId)
    if (!robot) return { ok: false, taskId: task.id, reason: '找不到指定機器人。' }
    if (robot.state === 'offline') return { ok: false, taskId: task.id, reason: '機器人目前離線。' }
    if (robot.battery < 20 && task.title !== '前往充電') return { ok: false, taskId: task.id, reason: '機器人電量不足 20%。' }
    const start = timeToSeconds(task.startTime)
    const end = timeToSeconds(task.endTime)
    const overlap = planned.find((other) => other.id !== task.id && other.robotId === task.robotId && (other.date || '2026-08-31') === (task.date || '2026-08-31') && start < timeToSeconds(other.endTime) && end > timeToSeconds(other.startTime))
    if (overlap) return { ok: false, taskId: task.id, reason: `與 ${overlap.id}「${overlap.title}」時間重疊。` }
  }
  changes.forEach((change) => {
    const target = state.tasks.find((entry) => entry.id === change.taskId)
    const plannedTask = planned.find((entry) => entry.id === change.taskId)
    Object.assign(target, plannedTask)
  })
  return { ok: true, tasks: changes.map((change) => state.tasks.find((entry) => entry.id === change.taskId)) }
}

const createTask = (input) => {
  const durationSeconds = Number(input.durationSeconds)
  const candidate = {
    ...input,
    id: `T${String(Math.max(0, ...state.tasks.map((task) => Number(/^T(\d+)$/.exec(task.id)?.[1]) || 0)) + 1).padStart(3, '0')}`,
    durationSeconds,
    endTime: secondsToTime(timeToSeconds(input.startTime) + durationSeconds),
    status: 'scheduled',
  }
  const validation = validateTask(candidate)
  if (!validation.ok) return validation
  state.tasks.push(candidate)
  const robot = state.robots.find((entry) => entry.id === candidate.robotId)
  robot.queuedTasks += 1
  robot.queuedTaskIds.push(candidate.id)
  state.notification = `已建立 ${candidate.id}「${candidate.title}」`
  window.setTimeout(() => { state.notification = '' }, 3200)
  return { ok: true, task: candidate }
}

const deleteTask = (taskId) => {
  const index = state.tasks.findIndex((task) => task.id === taskId)
  if (index < 0) return { ok: false, reason: '找不到任務。' }
  const [task] = state.tasks.splice(index, 1)
  const robot = state.robots.find((entry) => entry.id === task.robotId)
  if (robot) {
    robot.queuedTaskIds = robot.queuedTaskIds.filter((id) => id !== taskId)
    robot.queuedTasks = robot.queuedTaskIds.length
    if (robot.activeTaskId === taskId) {
      robot.activeTaskId = null
      if (robot.state === 'executing') robot.state = 'idle'
    }
  }
  return { ok: true, task }
}

const validateRobot = (candidate) => {
  const id = String(candidate.id || '').trim()
  const name = String(candidate.name || '').trim()
  const namespace = normalizeRosNamespace(candidate.rosNamespace)
  if (!name) return { ok: false, field: 'name', reason: '機器人名稱不可為空。' }
  if (!id) return { ok: false, field: 'id', reason: 'Robot ID 不可為空。' }
  if (state.robots.some((robot) => robot.id.toLowerCase() === id.toLowerCase())) return { ok: false, field: 'id', reason: `Robot ID「${id}」已存在。` }
  if (!namespace) return { ok: false, field: 'rosNamespace', reason: 'ROS Namespace 不可為空。' }
  if (state.robots.some((robot) => normalizeRosNamespace(robot.rosNamespace).toLowerCase() === namespace.toLowerCase())) return { ok: false, field: 'rosNamespace', reason: `ROS Namespace「${namespace}」已被使用。` }
  if (!ROBOT_NAV_GRAPHS.some((graph) => graph.index === Number(candidate.navGraphIndex))) return { ok: false, field: 'navGraphIndex', reason: '選擇的 Navigation Graph 不存在或不允許機器人使用。' }
  if (!GRAPH_0_CHARGING_WAYPOINTS.includes(candidate.chargingWaypoint)) return { ok: false, field: 'chargingWaypoint', reason: 'Charging Waypoint 不存在於 Graph 0。' }
  if (!Number.isFinite(Number(candidate.battery)) || Number(candidate.battery) < 0 || Number(candidate.battery) > 100) return { ok: false, field: 'battery', reason: '目前電量必須介於 0～100。' }
  for (const [field, label] of [['maxSpeedMps', '最大速度'], ['maxPayloadKg', '最大負載'], ['footprintRadiusM', '機器人半徑']]) {
    if (candidate[field] !== null && candidate[field] !== '' && Number(candidate[field]) < 0) return { ok: false, field, reason: `${label}不可為負數。` }
  }
  return { ok: true }
}

const addRobot = (input) => {
  const candidate = {
    ...commonRobot,
    ...input,
    id: String(input.id || '').trim(),
    name: String(input.name || '').trim(),
    rosNamespace: normalizeRosNamespace(input.rosNamespace),
    navGraphIndex: Number(input.navGraphIndex),
    battery: Number(input.battery),
    batteryCapacityWh: input.batteryCapacityWh === '' ? null : Number(input.batteryCapacityWh),
    minimumTaskBattery: input.minimumTaskBattery === '' ? null : Number(input.minimumTaskBattery),
    rechargeThreshold: input.rechargeThreshold === '' ? null : Number(input.rechargeThreshold),
    maxPayloadKg: input.maxPayloadKg === '' ? null : Number(input.maxPayloadKg),
    maxSpeedMps: input.maxSpeedMps === '' ? null : Number(input.maxSpeedMps),
    footprintRadiusM: input.footprintRadiusM === '' ? null : Number(input.footprintRadiusM),
    state: 'offline',
    connectionState: 'disconnected',
    currentLocation: input.currentLocation || 'Charging Station A',
    currentWaypoint: input.chargingWaypoint,
    activeTaskId: null,
    queuedTaskIds: [],
    completedTaskIds: [],
    queuedTasks: 0,
    capabilities: [...(input.capabilities || [])],
  }
  const validation = validateRobot(candidate)
  if (!validation.ok) return validation
  const robot = makeRobot(candidate)
  state.robots.push(robot)
  state.notification = `已新增 ${robot.name}；ROS 2 尚未連線。`
  window.setTimeout(() => { state.notification = '' }, 3200)
  return { ok: true, robot }
}

export const demoFleetStore = {
  state: readonly(state),
  robots: computed(() => state.robots),
  tasks: computed(() => state.tasks),
  notification: computed(() => state.notification),
  validateTask,
  moveTask,
  moveTasks,
  createTask,
  deleteTask,
  validateRobot,
  addRobot,
}

export const fleetStore = demoFleetStore
