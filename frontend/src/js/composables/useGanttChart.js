import { computed, ref } from 'vue'
import { parseTaskTime } from '@/js/utils/time.js'

export const GANTT_ZOOM_MIN = 0.5
export const GANTT_ZOOM_MAX = 4
export const GANTT_ZOOM_STEP = 0.25

const resolveTickConfig = (z) => {
  if (z <= 0.6) return { tick: 120, label: 120 }
  if (z < 1.25) return { tick: 60, label: 60 }
  if (z < 1.75) return { tick: 30, label: 60 }
  if (z < 2.5) return { tick: 15, label: 30 }
  if (z < 3.25) return { tick: 15, label: 15 }
  return { tick: 5, label: 15 }
}

const resolveBuffer = (z) => {
  if (z <= 0.5) return 240
  if (z <= 0.6) return 180
  if (z <= 0.75) return 120
  if (z < 1) return 60
  return 0
}

export function useGanttChart(tasks, robots, robotNameMap) {
  const ganttZoom = ref(1)

  const ganttVisualScale = computed(() => Math.max(1, ganttZoom.value))

  const zoomIn = () => {
    ganttZoom.value = Math.min(GANTT_ZOOM_MAX, +(ganttZoom.value + GANTT_ZOOM_STEP).toFixed(2))
  }
  const zoomOut = () => {
    ganttZoom.value = Math.max(GANTT_ZOOM_MIN, +(ganttZoom.value - GANTT_ZOOM_STEP).toFixed(2))
  }
  const zoomReset = () => { ganttZoom.value = 1 }
  const setZoom = (v) => { ganttZoom.value = Math.max(GANTT_ZOOM_MIN, Math.min(GANTT_ZOOM_MAX, +v)) }

  const resolveEnd = (task) => {
    const s = parseTaskTime(task.startTime)
    return task.endTime ? parseTaskTime(task.endTime) : s + 60
  }

  const ganttChart = computed(() => {
    const validTasks = tasks.filter((task) => {
      const start = parseTaskTime(task.startTime)
      return start !== Number.MAX_SAFE_INTEGER
    })

    if (validTasks.length === 0) {
      return { rows: [], ticks: [], rangeStart: 0, rangeEnd: 0 }
    }

    const minStart = Math.min(...validTasks.map((t) => parseTaskTime(t.startTime)))
    const maxEnd = Math.max(...validTasks.map((t) => resolveEnd(t)))

    const z = ganttZoom.value
    const { tick: tickInterval, label: labelInterval } = resolveTickConfig(z)
    const bufferMinutes = resolveBuffer(z)

    const rangeStart = Math.max(0, Math.floor((minStart - bufferMinutes) / tickInterval) * tickInterval)
    const rangeEnd = Math.min(24 * 60, Math.ceil((maxEnd + bufferMinutes) / tickInterval) * tickInterval)
    const total = Math.max(rangeEnd - rangeStart, 1)

    const ticks = []
    for (let m = rangeStart; m <= rangeEnd; m += tickInterval) {
      const h = Math.floor(m / 60)
      const mm = m % 60
      const isMajor = m % labelInterval === 0
      ticks.push({
        key: `tick-${m}`,
        label: isMajor ? `${String(h).padStart(2, '0')}:${String(mm).padStart(2, '0')}` : '',
        left: ((m - rangeStart) / total) * 100,
        isMajor,
      })
    }

    const groups = new Map()
    robots.forEach((r) => groups.set(r.id, []))
    validTasks.forEach((task) => {
      if (!groups.has(task.robot)) groups.set(task.robot, [])
      const start = parseTaskTime(task.startTime)
      const end = resolveEnd(task)
      groups.get(task.robot).push({
        ...task,
        left: ((start - rangeStart) / total) * 100,
        width: ((end - start) / total) * 100,
      })
    })

    const rows = []
    groups.forEach((bars, robotId) => {
      if (bars.length === 0) return
      rows.push({
        robotId,
        robotName: robotNameMap.value[robotId] || robotId,
        bars,
      })
    })

    return { rows, ticks, rangeStart, rangeEnd }
  })

  return {
    ganttZoom,
    ganttVisualScale,
    ganttChart,
    zoomIn,
    zoomOut,
    zoomReset,
    setZoom,
    GANTT_ZOOM_MIN,
    GANTT_ZOOM_MAX,
  }
}
