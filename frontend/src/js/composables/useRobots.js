import { computed, reactive, ref, onMounted, onUnmounted } from 'vue'
import { initialRobots } from '@/js/data/robots.js'
import { connectionConfig } from '@/js/data/connection.js'

const API_URL = `${connectionConfig.apiBaseUrl}/api/robots`
const POLL_INTERVAL = 1000

export function useRobots() {
  const robots = reactive(initialRobots.map((r) => ({ ...r })))
  const selectedRobotId = ref(robots[0]?.id ?? '')
  const connectionInfo = ref({ url: '', status: 'disconnected', failMessage: '' })
  const pendingRobots = ref([])

  let timer = null
  let lastRetryCount = 0
  let retryFailureCallback = null

  const selectedRobot = computed(
    () => robots.find((r) => r.id === selectedRobotId.value) ?? robots[0]
  )

  const robotNameMap = computed(() => {
    const map = {}
    robots.forEach((r) => { map[r.id] = r.name })
    return map
  })

  const selectRobot = (robotId) => { selectedRobotId.value = robotId }

  function markRobotsOffline() {
    for (const robot of robots) {
      robot.status = '離線'
      robot.modeText = '離線'
      robot.battery = 0
      robot.currentTask = '—'
      robot.location = '—'
      robot.signal = '—'
      robot.connectionIp = ''
      robot.uptime = ''
      robot.completedToday = 0
      robot.lastUpdate = null
      robot.currentTaskDetail = {
        taskNo: '—',
        title: '尚未連線',
        progress: 0,
        step: '',
        startedAt: '—',
        eta: '—',
        payload: '無',
      }
    }
  }

  let autoConnectSent = false

  async function fetchRobots() {
    try {
      const res = await fetch(API_URL)
      if (!res.ok) return

      const data = await res.json()
      connectionInfo.value = data.connection
      pendingRobots.value = data.pendingRobots || []

      const newRetryCount = data.connection.retryCount ?? 0
      if (newRetryCount > lastRetryCount && retryFailureCallback) {
        retryFailureCallback(newRetryCount, data.connection.url)
      }
      lastRetryCount = newRetryCount

      if (data.connection.status === 'disconnected' && newRetryCount === 0 && !autoConnectSent) {
        autoConnectSent = true
        connectToUrl(connectionConfig.rosBridgeUrl)
      }
      if (data.connection.status === 'connected') {
        autoConnectSent = false
      }

      if (data.connection.status === 'connected' && data.robots && data.robots.length > 0) {
        for (const remote of data.robots) {
          const idx = robots.findIndex((r) => r.id === remote.id)
          if (idx !== -1) {
            Object.assign(robots[idx], {
              name: remote.name,
              model: remote.model,
              status: remote.status,
              battery: remote.battery,
              currentTask: remote.currentTask,
              location: remote.location,
              signal: remote.signal,
              connectionIp: remote.connectionIp,
              rosName: remote.rosName,
              modeText: remote.modeText,
              uptime: remote.uptime || '',
              firmware: remote.firmware || '',
              x: remote.x,
              y: remote.y,
              levelName: remote.levelName,
              lastUpdate: remote.lastUpdate,
              currentTaskDetail: remote.currentTaskDetail,
            })
          } else {
            robots.push({
              ...remote,
              uptime: '',
              completedToday: 0,
              lastMaintenance: '',
              nextMaintenance: '',
              firmware: remote.firmware || '',
            })
          }
        }
      } else if (data.connection.status !== 'connected') {
        markRobotsOffline()
      }

    } catch {
      connectionInfo.value = { url: '', status: 'disconnected', failMessage: '' }
      markRobotsOffline()
    }
  }

  async function connectToUrl(url) {
    try {
      await fetch(`${API_URL}/connect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      })
    } catch { /* will show disconnected via polling */ }
  }

  async function disconnectFromBridge() {
    try {
      await fetch(`${API_URL}/disconnect`, { method: 'POST' })
    } catch { /* will show disconnected via polling */ }
  }

  async function confirmRobot(rosName, displayName) {
    try {
      await fetch(`${API_URL}/confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rosName, displayName }),
      })
    } catch { /* will retry on next poll */ }
  }

  onMounted(() => {
    fetchRobots()
    timer = setInterval(fetchRobots, POLL_INTERVAL)
  })

  onUnmounted(() => {
    if (timer) clearInterval(timer)
  })

  return {
    robots, selectedRobotId, selectedRobot, robotNameMap, selectRobot,
    connectionInfo, pendingRobots, connectToUrl, disconnectFromBridge, confirmRobot,
    onRetryFailure: (cb) => { retryFailureCallback = cb },
  }
}
