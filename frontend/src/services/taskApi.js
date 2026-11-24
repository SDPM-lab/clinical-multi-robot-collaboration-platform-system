import { t } from '@/i18n/index.js'
import { dispatchWaypointLabels, PPO_TASK_WAYPOINT_IDS } from '@/config/dispatchDestinations.js'
import { TASK_TYPE_BY_LABEL } from '@/config/taskTypes.js'
import { sessionFetch } from './sessionApi.js'

const baseUrl = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
const taskWaypointIds = new Set(PPO_TASK_WAYPOINT_IDS)
const taskLabels = Object.fromEntries(Object.entries(TASK_TYPE_BY_LABEL).map(([label, value]) => [value.toLowerCase(), label]))

async function apiFetch(url, options) {
  try { return await sessionFetch(url, options) }
  catch (error) { throw new Error(t(error.code === 'connection_error' ? 'dispatch.connectionError' : 'dispatch.apiError')) }
}
async function responseError(response) {
  const text = await response.text()
  let detail = ''
  try {
    const body = JSON.parse(text)
    if (body.code === 'reschedule_dispatch_cancellation_unsupported') {
      return new Error(t('dispatchUx.rescheduleUnavailable'))
    }
    detail = body.errors ? Object.values(body.errors).flat().join(' ') : body.detail || ''
  } catch {
    // Only show plain-text API descriptions, not HTML or raw server status pages.
    if (text.trim() && !/[<>]/.test(text) && !/^(HTTP\s*\d+|Forbidden|Unauthorized|Not Found|Internal Server Error)$/i.test(text.trim())) detail = text
  }
  if (response.status === 503 && detail.trim() === '外部派工服務尚未支援撤回舊指派，原任務已保留，暫時無法重新排程。') {
    return new Error(t('dispatchUx.rescheduleUnavailable'))
  }
  if (detail) return new Error(detail)
  const key = response.status === 403 ? 'requestDenied' : response.status === 401 ? 'signInRequired'
    : response.status === 404 ? 'apiNotFound' : response.status >= 500 ? 'serverUnavailable' : 'apiError'
  return new Error(t(`dispatch.${key}`))
}
async function request(path, options = {}) {
  const response = await apiFetch(`${baseUrl}/api/v1/task${path}`, options)
  if (!response.ok) {
    throw await responseError(response)
  }
  return response.status === 204 ? null : response.json()
}
export function toScheduleTask(task) {
  const date = new Date(task.scheduledAt || task.createdAt)
  const pad = value => String(value).padStart(2, '0')
  const title = taskLabels[String(task.taskType).toLowerCase()] || task.taskType
  return {
    ...task, title, type: title, robotId: task.assignedRobot,
    source: dispatchWaypointLabels[task.source] || task.source,
    destination: dispatchWaypointLabels[task.destination] || task.destination,
    date: `${date.getFullYear()}-${pad(date.getMonth()+1)}-${pad(date.getDate())}`,
    startTime: `${pad(date.getHours())}:${pad(date.getMinutes())}:00`,
    // The backend does not provide an estimated duration yet.
    endTime: `${pad(date.getHours())}:${pad(date.getMinutes())}:00`,
  }
}
export const taskApi = {
  async getPlaces() {
    const response = await apiFetch(`${baseUrl}/api/v1/place`)
    if (!response.ok) throw await responseError(response)
    const places = await response.json()
    if (!Array.isArray(places) || places.length !== PPO_TASK_WAYPOINT_IDS.length ||
      places.some((place, index) => place?.id !== PPO_TASK_WAYPOINT_IDS[index] || place?.index !== index)) {
      throw new Error(t('dispatch.apiError'))
    }
    return places
  },
  async getRobotSnapshot() {
    const response = await apiFetch(`${baseUrl}/api/robots`)
    if (!response.ok) throw await responseError(response)
    return response.json()
  },
  async getRobots() {
    const response = await apiFetch(`${baseUrl}/api/robots`)
    if (!response.ok) throw await responseError(response)
    const { robots } = await response.json()
    const states = { '待命':'idle', '在線':'idle', '忙碌':'busy', '已指派待執行':'assigned', '暫停':'paused', '待命中': 'idle', '執行任務中': 'busy', '充電中': 'charging', '緊急停止': 'error', '離線': 'offline' }
    return robots.map(robot => ({ ...robot, state: states[robot.status] || 'unknown' }))
  },
  getTaskRecords() { return request('') },
  async getTasks() { return (await request('')).map(toScheduleTask)   },
  async createTask(payload) {
    if (!taskWaypointIds.has(payload.source) || !taskWaypointIds.has(payload.destination)) throw new Error(t('dispatch.invalidLocations'))
    return request('', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
      taskType: payload.taskType, source: payload.source, destination: payload.destination, priority: payload.priority,
      robotId: payload.robotId ?? null, scheduledAt: payload.scheduledAt, note: payload.note || null,
    }) })
  },
  deleteTask(id) { return request(`/${encodeURIComponent(id)}`, { method: 'DELETE' }) },
  updatePriority(id, priority) {
    return request(`/${encodeURIComponent(id)}/priority`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ priority }) })
  },
  updateSchedule(id, scheduledAt) {
    return request(`/${encodeURIComponent(id)}/schedule`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ scheduledAt }) })
  },
  completeSimulatedArrival(id, robotId, source, destination) {
    return request(`/${encodeURIComponent(id)}/simulation/arrive`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ robotId, source, destination }) })
  },
}
