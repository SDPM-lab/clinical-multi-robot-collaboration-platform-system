import { timeToSeconds } from '@/stores/demoFleetStore.js'

export const WORKDAY_START = 8 * 3600
export const WORKDAY_END = 18 * 3600
export const ZOOM_LEVELS = Object.freeze([1, 2, 5])
export const TICK_STEPS = Object.freeze({ far: 30 * 60, normal: 5 * 60, close: 60, detail: 10 })
export const BUBBLE_LEVELS = Object.freeze([-2, 2, -1, 1, -3, 3])
export const priorityBubbleSize = Object.freeze({ low: 34, normal: 46, high: 60 })

export const normalizePriority = (priority) => {
  if (typeof priority === 'number') return priority >= 80 ? 'high' : priority >= 40 ? 'normal' : 'low'
  return priorityBubbleSize[priority] ? priority : 'normal'
}

export const getDragSnapSeconds = (pixelsPerMinute) => {
  if (pixelsPerMinute >= 24) return 10
  if (pixelsPerMinute >= 12) return 60
  return 5 * 60
}

export const getNextZoom = (current, direction) => {
  const index = ZOOM_LEVELS.reduce((best, value, candidate) => (
    Math.abs(value - current) < Math.abs(ZOOM_LEVELS[best] - current) ? candidate : best
  ), 0)
  return ZOOM_LEVELS[Math.max(0, Math.min(ZOOM_LEVELS.length - 1, index + direction))]
}

export const getAnchoredScrollLeft = ({ oldZoom, newZoom, viewportWidth, scrollLeft, cursorX }) => {
  const safeWidth = Math.max(viewportWidth, 1)
  const anchorRatio = (scrollLeft + cursorX) / (safeWidth * oldZoom)
  const next = anchorRatio * safeWidth * newZoom - cursorX
  return Math.max(0, Math.min(safeWidth * newZoom - safeWidth, next))
}

export const snapTaskStart = (seconds, durationSeconds, step = 5 * 60) => {
  const snapped = Math.round(seconds / step) * step
  return Math.max(WORKDAY_START, Math.min(WORKDAY_END - durationSeconds, snapped))
}

export const assignBubbleLevels = (tasks, secondsPerPixel) => {
  const occupied = new Map(BUBBLE_LEVELS.map((level) => [level, []]))
  return [...tasks].sort((first, second) => first.startSeconds - second.startSeconds).map((task) => {
    const paddingSeconds = 14 * secondsPerPixel
    const halfDuration = (task.size / 2) * secondsPerPixel
    const level = BUBBLE_LEVELS.find((candidate) => occupied.get(candidate).every((entry) => (
      Math.abs(entry.startSeconds - task.startSeconds) > entry.halfDuration + halfDuration + paddingSeconds
    ))) ?? BUBBLE_LEVELS.at(-1)
    occupied.get(level).push({ startSeconds: task.startSeconds, halfDuration })
    return { ...task, level }
  })
}

export const hasTimelineConflict = ({ task, startSeconds, drafts, tasks, robots }) => {
  const robot = robots.find((entry) => entry.id === task.robotId)
  if (!robot) return '找不到指定機器人。'
  if (robot.state === 'offline') return '機器人目前離線。'
  if (robot.battery < 20 && task.title !== '前往充電') return '機器人電量不足 20%。'
  const endSeconds = startSeconds + task.durationSeconds
  const overlap = tasks.find((other) => {
    if (other.id === task.id || other.robotId !== task.robotId) return false
    const otherStart = drafts[other.id] ?? timeToSeconds(other.startTime)
    return startSeconds < otherStart + other.durationSeconds && endSeconds > otherStart
  })
  return overlap ? `與 ${overlap.id}「${overlap.title}」時間重疊。` : ''
}

export const shiftIsoDate = (isoDate, offsetDays) => {
  const date = new Date(`${isoDate}T12:00:00`)
  date.setDate(date.getDate() + offsetDays)
  return date.toISOString().slice(0, 10)
}
