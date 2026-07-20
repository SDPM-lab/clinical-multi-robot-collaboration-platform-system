import { computed, reactive, ref } from 'vue'
import { initialAlerts } from '@/js/data/alerts.js'
import { parseTaskTime } from '@/js/utils/time.js'

export function useAlerts(robots, robotNameMap) {
  const alerts = reactive(initialAlerts.map((a) => ({ ...a })))
  const selectedAlertSource = ref('all')

  const alertSourceLabel = (source) => {
    if (source === 'console') return '中控台'
    return robotNameMap.value[source] || source
  }

  const alertSourceOptions = computed(() => {
    const counts = { all: alerts.length, console: 0 }
    robots.forEach((r) => { counts[r.id] = 0 })
    alerts.forEach((a) => { if (counts[a.source] !== undefined) counts[a.source] += 1 })
    const opts = [{ value: 'all', label: '全部', count: counts.all }]
    opts.push({ value: 'console', label: '中控台', count: counts.console })
    robots.forEach((r) => opts.push({ value: r.id, label: r.name, count: counts[r.id] }))
    return opts
  })

  const filteredAlerts = computed(() => {
    const arr = selectedAlertSource.value === 'all'
      ? alerts.slice()
      : alerts.filter((a) => a.source === selectedAlertSource.value)
    return arr.sort((a, b) => parseTaskTime(b.time) - parseTaskTime(a.time))
  })

  const unreadAlertCount = computed(() => alerts.filter((a) => !a.read).length)

  const markAlertRead = (id) => {
    const target = alerts.find((a) => a.id === id)
    if (target) target.read = true
  }

  const markAllAlertsRead = () => alerts.forEach((a) => { a.read = true })

  let alertSeq = alerts.length + 1
  const toastQueue = reactive([])

  const addAlert = ({ source = 'console', type = '資訊', level = '低', title, detail, narrative = '' }) => {
    const now = new Date()
    const time = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`
    const id = `alert-auto-${alertSeq++}`
    alerts.unshift({ id, source, type, level, title, detail, narrative, time, taskId: null, read: false })
    toastQueue.push({ id, type, level, title, detail, time })
    setTimeout(() => dismissToast(id), 5000)
  }

  const dismissToast = (id) => {
    const idx = toastQueue.findIndex((t) => t.id === id)
    if (idx !== -1) toastQueue.splice(idx, 1)
  }

  return {
    alerts,
    selectedAlertSource,
    alertSourceLabel,
    alertSourceOptions,
    filteredAlerts,
    unreadAlertCount,
    markAlertRead,
    markAllAlertsRead,
    addAlert,
    toastQueue,
    dismissToast,
  }
}
