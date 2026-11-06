export const batteryRanges = ['Day', 'Weekly', 'Monthly']

export const robotStatusLabels = {
  busy: '忙碌', charging: '充電中', idle: '待命', offline: '離線',
  error: '異常', absent: '未在此樓層', unknown: '樓層資料未知',
}

const demoProfiles = {
  R01: { values: [94, 91, 88, 90, 86, 84, 82], status: 'busy', task: '藥品配送', taskId: 'T001' },
  R02: { values: [62, 57, 51, 46, 41, 37, 34], status: 'charging', task: '檢驗報告運送', taskId: 'T014' },
  R03: { values: [48, 43, 39, 33, 28, 23, 18], status: 'idle', task: '病房物資補充', taskId: 'T021' },
}

const rangeOffsets = {
  Day: [0, 1, 2, 3, 4, 5, 6].map((hour) => hour * 60 * 60 * 1000),
  Weekly: [0, 1, 2, 3, 4, 5, 6].map((day) => day * 24 * 60 * 60 * 1000),
  Monthly: [0, 5, 10, 15, 20, 25, 30].map((day) => day * 24 * 60 * 60 * 1000),
}

function timestampOf(value) {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}/.test(value)) return null
  const timestamp = Date.parse(value)
  return Number.isFinite(timestamp) ? timestamp : null
}

function taskFields(row, robotId) {
  const detail = row.details?.[robotId] || {}
  return {
    status: detail.status ?? row.statuses?.[robotId],
    task: detail.task ?? row.tasks?.[robotId],
    taskId: detail.taskId ?? row.taskIds?.[robotId],
  }
}

export function fixedDemoBatteryHistory(robotId, range = 'Day', latestPoint = null) {
  const profile = demoProfiles[robotId] || demoProfiles.R01
  const latest = Number.isFinite(latestPoint?.timestamp) ? latestPoint.timestamp : Date.parse('2026-09-14T14:00:00+08:00')
  const offsets = rangeOffsets[range] || rangeOffsets.Day
  const difference = Number.isFinite(latestPoint?.value) ? latestPoint.value - profile.values.at(-1) : 0
  return profile.values.map((value, index) => ({
    value: Math.max(0, Math.min(100, value + difference)),
    timestamp: latest - offsets[offsets.length - 1 - index],
    status: profile.status,
    task: profile.task,
    taskId: profile.taskId,
    demo: true,
    ...(index === profile.values.length - 1 && latestPoint ? Object.fromEntries(Object.entries(latestPoint).filter(([, field]) => field != null)) : {}),
  }))
}

export function selectBatteryHistory(history, rolling, robotId, range, now = Date.now()) {
  const raw = [
    ...history.filter((row) => Number.isFinite(row.batteries?.[robotId])).map((row) => ({
      value: row.batteries[robotId],
      time: row.time,
      timestamp: timestampOf(row.timestamp ?? row.updatedAt ?? (row.date && row.time ? `${row.date}T${row.time}` : row.time)),
      ...taskFields(row, robotId),
    })),
    ...(rolling[robotId] || []).map((point) => ({ ...point, timestamp: timestampOf(point.timestamp ?? point.updatedAt) })),
  ].filter((point) => Number.isFinite(point.value) && (point.timestamp === null || point.timestamp <= now))

  const unique = new Map()
  for (const point of raw) unique.set(point.timestamp ?? `time:${point.time}`, { ...point, value: Math.max(0, Math.min(100, point.value)) })
  const points = [...unique.values()].sort((a, b) => (a.timestamp !== null && b.timestamp !== null ? a.timestamp - b.timestamp : 0))

  if (range === 'Day') {
    const dated = points.filter((point) => point.timestamp !== null)
    if (!dated.length) return points.slice(-30)
    const latestDate = new Date(dated.at(-1).timestamp)
    return dated.filter((point) => {
      const date = new Date(point.timestamp)
      return date.getFullYear() === latestDate.getFullYear() && date.getMonth() === latestDate.getMonth() && date.getDate() === latestDate.getDate()
    }).slice(-30)
  }

  const latestTimestamp = points.filter((point) => point.timestamp !== null).at(-1)?.timestamp
  if (!Number.isFinite(latestTimestamp)) return []
  const start = new Date(latestTimestamp)
  start.setHours(0, 0, 0, 0)
  if (range === 'Weekly') start.setDate(start.getDate() - 6)
  else start.setDate(1)

  const buckets = new Map()
  for (const point of points) {
    if (point.timestamp === null || point.timestamp < start.getTime()) continue
    const date = new Date(point.timestamp)
    buckets.set(`${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`, point)
  }
  return [...buckets.values()]
}

export function batteryPointTime(point, range = 'Day') {
  if (point.timestamp === null) return point.time || '時間未提供'
  const date = new Date(point.timestamp)
  if (range === 'Monthly' || range === 'Weekly') return `${date.getMonth() + 1}/${date.getDate()}`
  return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

export function formatBatteryTimestamp(point) {
  if (!Number.isFinite(point?.timestamp)) return point?.time || '時間未提供'
  const date = new Date(point.timestamp)
  const pad = (value) => String(value).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}
