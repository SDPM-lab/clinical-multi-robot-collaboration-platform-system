import { t } from '@/i18n/index.js'
import { dispatchWaypointLabels } from '@/config/dispatchDestinations.js'
import { TASK_TYPE_BY_LABEL } from '@/config/taskTypes.js'

const baseUrl = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
const waypointIds = Object.fromEntries(Object.entries(dispatchWaypointLabels).map(([id, label]) => [label, id]))
const taskLabels = Object.fromEntries(Object.entries(TASK_TYPE_BY_LABEL).map(([label, value]) => [value.toLowerCase(), label]))

async function apiFetch(url, options) {
  try { return await fetch(url, options) }
  catch { throw new Error(t('dispatch.connectionError')) }
}
async function responseError(response) {
  const text = await response.text()
  let detail = ''
  try {
    const body = JSON.parse(text)
    detail = body.errors ? Object.values(body.errors).flat().join(' ') : body.detail || ''
  } catch {
    // Only show plain-text API descriptions, not HTML or raw server status pages.
    if (text.trim() && !/[<>]/.test(text) && !/^(HTTP\s*\d+|Forbidden|Unauthorized|Not Found|Internal Server Error)$/i.test(text.trim())) detail = text
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
    origin: dispatchWaypointLabels[task.source] || task.source,
    destination: dispatchWaypointLabels[task.destination] || task.destination,
    date: `${date.getFullYear()}-${pad(date.getMonth()+1)}-${pad(date.getDate())}`,
    startTime: `${pad(date.getHours())}:${pad(date.getMinutes())}:00`,
    // The backend does not provide an estimated duration yet.
    endTime: `${pad(date.getHours())}:${pad(date.getMinutes())}:00`,
  }
}
export const taskApi = {
  async getRobots() {
    const response = await apiFetch(`${baseUrl}/api/robots`)
    if (!response.ok) throw await responseError(response)
    const { robots } = await response.json()
    const states = { '待命中': 'idle', '執行任務中': 'busy', '充電中': 'charging', '緊急停止': 'error', '離線': 'offline' }
    return robots.map(robot => ({ ...robot, state: states[robot.status] || 'idle' }))
  },
  async getTasks() { return (await request('')).map(toScheduleTask) },
  async createTask(payload) {
    const origin = waypointIds[payload.origin]
    const destination = waypointIds[payload.destination]
    if (!origin || !destination) throw new Error('Invalid task waypoint')
    return request('', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
      taskType: payload.taskType, origin, destination, priority: payload.priority,
      robotId: payload.robotId ?? null, scheduledAt: payload.scheduledAt, note: payload.note || null,
    }) })
  },
  deleteTask(id) { return request(`/${encodeURIComponent(id)}`, { method: 'DELETE' }) },
  updateSchedule(id, scheduledAt) {
    return request(`/${encodeURIComponent(id)}/schedule`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ scheduledAt }) })
  },
}
