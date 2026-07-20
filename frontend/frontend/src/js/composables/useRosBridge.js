import { ref, onMounted, onUnmounted } from 'vue'
import { connectionConfig } from '@/js/data/connection.js'

const API_URL = `${connectionConfig.apiBaseUrl}/api/robots`
const STATUS_MAP = {
  connected: '已連線',
  connecting: '連線中...',
  disconnected: '未連線',
}

export function useRosBridge() {
  const rosMapCanvas = ref(null)
  const rosBridgeUrl = ref('')
  const rosBridgeStatus = ref('查詢中...')

  let timer = null

  async function fetchStatus() {
    try {
      const res = await fetch(API_URL)
      if (!res.ok) throw new Error()
      const data = await res.json()
      rosBridgeUrl.value = data.connection.url
      rosBridgeStatus.value = STATUS_MAP[data.connection.status] || data.connection.status
    } catch {
      rosBridgeStatus.value = '後端未啟動'
    }
  }

  const reconnect = () => {
    rosBridgeStatus.value = '查詢中...'
    fetchStatus()
  }

  onMounted(() => {
    fetchStatus()
    timer = setInterval(fetchStatus, 1000)
  })

  onUnmounted(() => {
    if (timer) clearInterval(timer)
  })

  return { rosMapCanvas, rosBridgeUrl, rosBridgeStatus, reconnect }
}
