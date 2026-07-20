import { computed, reactive, onMounted } from 'vue'
import { parseTaskTime } from '@/js/utils/time.js'
import { connectionConfig } from '@/js/data/connection.js'

const API = `${connectionConfig.apiBaseUrl}/api/v1/task`

function mapTask(t) {
  return {
    id:          t.id,
    title:       t.title,
    place:       t.place,
    items:       t.items,
    robot:       t.robot ?? null,
    status:      t.status,
    startTime:   t.start ? t.start.substring(11, 16) : '',
    startDate:   t.start ? t.start.substring(0,  10) : '',
    endTime:     t.end   ? t.end.substring(11, 16)   : '',
    endDate:     t.end   ? t.end.substring(0,  10)   : '',
    description: t.note ?? '',
  }
}

export function useTasks(selectedRobotId) {
  const tasks = reactive([])

  const loadTasks = async () => {
    const res = await fetch(API)
    if (!res.ok) throw new Error(await res.text())
    const data = await res.json()
    tasks.splice(0, tasks.length, ...data.map(mapTask))
  }

  onMounted(loadTasks)

  const filteredTasks = computed(() =>
    tasks
      .filter((task) => task.robot === selectedRobotId.value)
      .slice()
      .sort((a, b) => parseTaskTime(a.startTime) - parseTaskTime(b.startTime))
  )

  const historyTasks = computed(() =>
    tasks
      .slice()
      .sort((a, b) => parseTaskTime(b.startTime) - parseTaskTime(a.startTime))
  )

  const stats = computed(() => ({
    pending:   tasks.filter((task) => task.status !== 'complete').length,
    completed: tasks.filter((task) => task.status === 'complete').length,
  }))

  const assignTask = async (taskData) => {
    const body = new FormData()
    body.append('title', taskData.title)
    body.append('place', taskData.place)
    if (taskData.startTime) body.append('startTime', taskData.startTime)
    if (taskData.robot && taskData.robot !== 'auto') body.append('robot', taskData.robot)
    if (taskData.description) body.append('note', taskData.description)
    taskData.items.forEach((item) => body.append('items', item))

    const res = await fetch(API, { method: 'POST', body })
    if (!res.ok) throw new Error(await res.text())

    await loadTasks()
  }

  const abortTask = async (taskId) => {
    const res = await fetch(`${API}/${taskId}/abort`, { method: 'PATCH' })
    if (!res.ok) throw new Error(await res.text())
    const task = tasks.find((t) => t.id === taskId)
    if (task) task.status = 'abort'
  }

  const confirmTask = async (taskId) => {
    const res = await fetch(`${API}/${taskId}/confirm`, { method: 'PATCH' })
    if (!res.ok) throw new Error(await res.text())
    dismissTask(taskId)
  }

  const removeTask = async (taskId) => {
    const res = await fetch(`${API}/${taskId}`, { method: 'DELETE' })
    if (!res.ok) throw new Error(await res.text())
    const index = tasks.findIndex((t) => t.id === taskId)
    if (index !== -1) tasks.splice(index, 1)
  }

  const dismissTask = (taskId) => {
    const index = tasks.findIndex((t) => t.id === taskId)
    if (index !== -1) tasks.splice(index, 1)
  }

  const findTask = (taskId) => tasks.find((t) => t.id === taskId) || null
  const findTaskById = (taskId) => tasks.find((t) => t.id === taskId) || null

  return {
    tasks,
    filteredTasks,
    historyTasks,
    stats,
    loadTasks,
    assignTask,
    abortTask,
    confirmTask,
    removeTask,
    dismissTask,
    findTask,
    findTaskById,
  }
}
