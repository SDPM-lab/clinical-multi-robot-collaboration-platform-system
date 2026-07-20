<script setup lang="ts">
import { computed, ref, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AssignTaskForm from '@/components/AssignTaskForm.vue'
import TaskModal from '@/components/TaskModal.vue'
import AlertDetailDialog from '@/components/AlertDetailDialog.vue'
import NotificationBell from '@/components/NotificationBell.vue'
import ToastNotification from '@/components/ToastNotification.vue'

import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { PlusIcon } from '@lucide/vue'
import { Separator } from '@/components/ui/separator'
import { Input } from '@/components/ui/input'

import { menuItems, sectionMap } from '@/js/data/menu.js'
import { useRobots } from '@/js/composables/useRobots.js'
import { useTasks } from '@/js/composables/useTasks.js'
import { useAlerts } from '@/js/composables/useAlerts.js'
import { useGanttChart, GANTT_ZOOM_MIN, GANTT_ZOOM_MAX } from '@/js/composables/useGanttChart.js'
import { useRosBridge } from '@/js/composables/useRosBridge.js'
import { useDashboardModal } from '@/js/composables/useDashboardModal.js'
import { getRobotTask } from '@/js/data/robotTasks.js'

const route = useRoute()
const router = useRouter()

const {
  robots, selectedRobotId, selectedRobot, robotNameMap, selectRobot,
  connectionInfo, pendingRobots, confirmRobot, onRetryFailure,
} = useRobots()

const {
  tasks, filteredTasks, historyTasks, stats,
  assignTask, abortTask, confirmTask: apiConfirmTask,
  removeTask, dismissTask, findTask, findTaskById,
} = useTasks(selectedRobotId)

const {
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
} = useAlerts(robots, robotNameMap)
const {
  ganttZoom,
  ganttVisualScale,
  ganttChart,
  zoomIn: ganttZoomIn,
  zoomOut: ganttZoomOut,
  zoomReset: ganttZoomReset,
  setZoom: ganttSetZoom,
} = useGanttChart(tasks, robots, robotNameMap)
const { rosMapCanvas, rosBridgeUrl, rosBridgeStatus, reconnect: reconnectRosBridge } = useRosBridge()
const { activeModal, isModalOpen, modalTitle, resultTitle, confirmMessage, openModal, closeModal } = useDashboardModal()

const activeMenu = computed(() => {
  const name = route.name as string
  if (name === 'robot-detail' || name === 'robot-task-detail') return 'robots'
  return name || 'dispatch'
})
const navigateTo = (name: string) => { router.push({ name }) }

const bellPopoverOpen = ref(false)

const isConnected = computed(() => connectionInfo.value.status === 'connected')
const isConnecting = computed(() => connectionInfo.value.status === 'connecting')
const connectionLabel = computed(() => {
  const s = connectionInfo.value.status
  if (s === 'connected') return '已連線'
  if (s === 'connecting') return '連線中...'
  return '未連線'
})

const TABLET_BREAKPOINT = 1024
const isSidebarCollapsed = ref(window.innerWidth <= TABLET_BREAKPOINT)
const toggleSidebar = () => { isSidebarCollapsed.value = !isSidebarCollapsed.value }

const onResize = () => {
  if (window.innerWidth <= TABLET_BREAKPOINT) {
    isSidebarCollapsed.value = true
  }
}
onMounted(() => window.addEventListener('resize', onResize))
onUnmounted(() => window.removeEventListener('resize', onResize))

function handleMenuClick(id: string) {
  navigateTo(id)
  if (window.innerWidth <= TABLET_BREAKPOINT) {
    isSidebarCollapsed.value = true
  }
}

const currentSection = computed(() => {
  if (route.name === 'robot-task-detail') {
    const t = getRobotTask(route.params.id as string, route.params.taskId as string)
    return {
      title: t?.name || '任務詳情',
      description: t?.code || '',
      badge: '任務步驟',
    }
  }
  if (route.name === 'robot-detail') {
    const r = robots.find((r: any) => r.id === route.params.id)
    return {
      title: r?.name || '機器人詳情',
      description: '',
      badge: '任務狀態',
    }
  }
  return sectionMap[activeMenu.value] ?? sectionMap.dispatch
})

const breadcrumbs = computed(() => {
  const crumbs: Array<{ label: string; to?: Record<string, any> }> = [
    { label: '首頁', to: { name: 'dispatch' } },
  ]
  if (route.name === 'robot-task-detail') {
    const r = robots.find((r: any) => r.id === route.params.id)
    const t = getRobotTask(route.params.id as string, route.params.taskId as string)
    crumbs.push({ label: '機器人狀態', to: { name: 'robots' } })
    crumbs.push({ label: r?.name || String(route.params.id), to: { name: 'robot-detail', params: { id: route.params.id } } })
    crumbs.push({ label: t?.name || String(route.params.taskId) })
  } else if (route.name === 'robot-detail') {
    crumbs.push({ label: '機器人狀態', to: { name: 'robots' } })
    const r = robots.find((r: any) => r.id === route.params.id)
    crumbs.push({ label: r?.name || String(route.params.id) })
  } else {
    crumbs.push({ label: currentSection.value.title })
  }
  return crumbs
})

const confirmingTaskId = ref<string | null>(null)
const pendingCancelTaskId = ref<string | null>(null)
const pendingCancelTask = computed(() => findTask(pendingCancelTaskId.value))

const handleAssignTask = async (taskData: any) => {
  try {
    await assignTask(taskData)
    if (taskData.robot !== 'auto') selectRobot(taskData.robot)
    closeModal()
  } catch (err: any) {
    resultTitle.value = '建立任務失敗'
    confirmMessage.value = err.message || '請確認輸入內容後重試'
    openModal('result')
  }
}

const requestCancelTask = (taskId: string) => {
  pendingCancelTaskId.value = taskId
  openModal('cancel')
}

const cancelTask = async () => {
  const task = pendingCancelTask.value
  const taskId = pendingCancelTaskId.value
  pendingCancelTaskId.value = null
  try {
    if (task?.status === 'idle') {
      await removeTask(taskId)
      resultTitle.value = '取消任務完成'
      confirmMessage.value = `任務「${task?.title || '此任務'}」已取消`
    } else {
      await abortTask(taskId)
      resultTitle.value = '取消任務完成'
      confirmMessage.value = `任務「${task?.title || '此任務'}」已中斷`
    }
  } catch (err: any) {
    resultTitle.value = '取消任務失敗'
    confirmMessage.value = err.message || '請稍後再試'
  }
  openModal('result')
}

const closeCancelDialog = () => {
  closeModal()
  pendingCancelTaskId.value = null
}

const confirmTask = async (taskId: string) => {
  const task = findTask(taskId)
  if (!task) return
  confirmingTaskId.value = taskId
  resultTitle.value = '已完成任務'
  confirmMessage.value = `任務「${task.title}」已完成，資料已匯入資料庫`
  try {
    await apiConfirmTask(taskId)
  } catch (err: any) {
    resultTitle.value = '確認任務失敗'
    confirmMessage.value = err.message || '請稍後再試'
  } finally {
    confirmingTaskId.value = null
    openModal('result')
  }
}

const closeConfirmResult = () => {
  closeModal()
  confirmMessage.value = ''
}

const selectedAlertId = ref<string | null>(null)
const selectedAlert = computed(() => alerts.find((a: any) => a.id === selectedAlertId.value) || null)
const selectedAlertTask = computed(() => {
  const alert = selectedAlert.value
  if (!alert || !alert.taskId) return null
  return findTaskById(alert.taskId)
})

const openAlertDetail = (alert: any) => {
  selectedAlertId.value = alert.id
  if (!alert.read) alert.read = true
  openModal('alertDetail')
}

const closeAlertDetail = () => {
  closeModal()
  selectedAlertId.value = null
}

const pendingStopRobotId = ref<string | null>(null)
const pendingStopRobot = computed(() => robots.find((r: any) => r.id === pendingStopRobotId.value) || null)

const requestEmergencyStop = (robotId: string) => {
  pendingStopRobotId.value = robotId
  openModal('emergencyStop')
}

const proceedToReconfirm = () => {
  openModal('emergencyStopReconfirm')
}

const confirmEmergencyStop = () => {
  const robot = pendingStopRobot.value
  if (robot) {
    robot.status = '待命'
    robot.currentTask = '緊急停止 — 已暫停所有動作'
  }
  pendingStopRobotId.value = null
  resultTitle.value = '緊急停止完成'
  confirmMessage.value = `「${robot?.name || '機器人'}」已緊急停止，所有任務暫停`
  openModal('result')
}

const closeEmergencyStopDialog = () => {
  closeModal()
  pendingStopRobotId.value = null
}

const registerMapCanvas = (el: any) => { rosMapCanvas.value = el }

const viewProps = computed(() => ({
  dispatch: {
    robots,
    selectedRobot: selectedRobot.value,
    selectedRobotId: selectedRobotId.value,
    filteredTasks: filteredTasks.value,
    confirmingTaskId: confirmingTaskId.value,
  },
  robots: {
    robots,
  },
  'robot-detail': {
    robots,
  },
  'robot-task-detail': {
    robots,
  },
  schedule: {
    ganttChart: ganttChart.value,
    ganttZoom: ganttZoom.value,
    ganttVisualScale: ganttVisualScale.value,
    zoomMin: GANTT_ZOOM_MIN,
    zoomMax: GANTT_ZOOM_MAX,
    historyTasks: historyTasks.value,
    robotNameMap: robotNameMap.value,
  },
  map: {
    robots,
    rosBridgeUrl: rosBridgeUrl.value,
    rosBridgeStatus: rosBridgeStatus.value,
  },
  alerts: {
    filteredAlerts: filteredAlerts.value,
    alertSourceOptions: alertSourceOptions.value,
    selectedAlertSource: selectedAlertSource.value,
    unreadAlertCount: unreadAlertCount.value,
    alertSourceLabel,
  },
}))


const pendingRobotName = ref('')
const pendingRobotRosName = ref('')

const handleConfirmNewRobot = () => {
  if (!pendingRobotRosName.value) return
  const name = pendingRobotName.value.trim() || pendingRobotRosName.value
  confirmRobot(pendingRobotRosName.value, name)
  pendingRobotRosName.value = ''
  pendingRobotName.value = ''
  closeModal()
}

const dismissPendingRobot = () => {
  pendingRobotRosName.value = ''
  pendingRobotName.value = ''
  closeModal()
}

watch(pendingRobots, (list) => {
  if (list.length > 0 && activeModal.value !== 'newRobot') {
    pendingRobotRosName.value = list[0]
    pendingRobotName.value = ''
    openModal('newRobot')
  }
})

onRetryFailure((count, url) => {
  addAlert({
    source: 'console',
    type: '異常',
    level: count >= 5 ? '高' : '中',
    title: `RosBridge 第 ${count} 次重連失敗`,
    detail: `無法連線至 ${url}，系統將持續嘗試重新連線。`,
    narrative: `系統嘗試連線至 RosBridge (${url}) 第 ${count} 次失敗。後端將每 5 秒自動重試，連線成功後將自動恢復。若長時間無法連線，請確認 RosBridge 服務是否啟動及網路狀態。`,
  })
})

const viewEvents = {
  dispatch: {
    'select-robot': selectRobot,
    'cancel-task': requestCancelTask,
    'confirm-task': confirmTask,
    'remove-task': async (id: string) => {
      try {
        await apiConfirmTask(id)
      } catch {
        dismissTask(id)
      }
    },
    'emergency-stop': requestEmergencyStop,
  },
  robots: {},
  'robot-detail': {},
  'robot-task-detail': {},
  schedule: {
    'zoom-in': ganttZoomIn,
    'zoom-out': ganttZoomOut,
    'zoom-reset': ganttZoomReset,
    'set-zoom': ganttSetZoom,
  },
  map: {
    reconnect: reconnectRosBridge,
    'register-canvas': registerMapCanvas,
  },
  alerts: {
    'select-source': (v: string) => { selectedAlertSource.value = v },
    'mark-read': markAlertRead,
    'mark-all-read': markAllAlertsRead,
    'open-detail': openAlertDetail,
  },
}
</script>

<template>
  <div class="app-layout flex flex-col h-screen overflow-hidden">
    <!-- Top Navbar -->
    <header class="navbar-top flex items-center justify-between px-3 bg-background border-b shrink-0 anim-fade-in-down">
      <div class="flex items-center gap-2">
        <Button variant="outline" size="sm" class="navbar-toggle-btn" @click="toggleSidebar" :aria-label="isSidebarCollapsed ? '展開選單' : '收合選單'">
          <span>☰</span>
        </Button>
        <div class="flex items-center gap-2">
          <span class="font-bold text-foreground">醫療機器人平台</span>
        </div>
        <Separator orientation="vertical" class="mx-1 h-5 hidden md:block" />
        <nav class="hidden md:flex items-center gap-1 text-sm">
          <template v-for="(crumb, i) in breadcrumbs" :key="i">
            <span v-if="i > 0" class="text-muted-foreground">/</span>
            <span
              v-if="crumb.to"
              class="text-muted-foreground cursor-pointer hover:text-foreground"
              @click="router.push(crumb.to)"
            >{{ crumb.label }}</span>
            <span v-else class="font-semibold text-foreground">{{ crumb.label }}</span>
          </template>
        </nav>
      </div>
      <div class="flex items-center gap-3">
        <NotificationBell
          :alerts="alerts"
          :unread-count="unreadAlertCount"
          v-model:open="bellPopoverOpen"
          @mark-all-read="markAllAlertsRead"
          @open-detail="openAlertDetail"
          @view-all="navigateTo('alerts')"
        />
        <div
          class="system-status flex items-center gap-2 px-2 py-1 rounded-full"
          :class="{
            'system-status--connected': isConnected,
            'system-status--connecting': isConnecting,
            'system-status--disconnected': !isConnected && !isConnecting,
          }"
          :title="connectionInfo.url"
        >
          <span
            class="status-dot-pulse"
            :class="{
              'status-dot--connected': isConnected,
              'status-dot--connecting': isConnecting,
              'status-dot--disconnected': !isConnected && !isConnecting,
            }"
          ></span>
          <span class="text-sm font-semibold hidden sm:inline"
            :class="{
              'text-emerald-600': isConnected,
              'text-amber-600': isConnecting,
              'text-red-500': !isConnected && !isConnecting,
            }"
          >{{ connectionLabel }}</span>
        </div>
      </div>
    </header>

    <div class="flex grow overflow-hidden">
      <!-- Sidebar Overlay -->
      <div
        v-if="!isSidebarCollapsed"
        class="sidebar-overlay"
        @click="isSidebarCollapsed = true"
      ></div>

      <!-- Left Sidebar -->
      <aside class="sidebar border-r bg-background anim-fade-in-left" :class="{ 'sidebar--collapsed': isSidebarCollapsed }">
        <nav class="grid gap-1 p-2">
          <button
            v-for="item in menuItems"
            :key="item.id"
            class="menu-item text-left"
            :class="{
              'menu-item--active': activeMenu === item.id,
              'hidden': isSidebarCollapsed
            }"
            :title="isSidebarCollapsed ? item.label : ''"
            @click="handleMenuClick(item.id)"
          >
            <span class="font-semibold">{{ item.label }}</span>
          </button>
        </nav>
      </aside>

      <!-- Main Content -->
      <main class="dashboard grow overflow-auto p-6 min-w-0">
        <div class="mb-6 anim-fade-in-up">
          <p class="eyebrow mb-1">{{ currentSection.badge }}</p>
          <h1 class="text-2xl font-bold text-foreground">{{ currentSection.title }}</h1>
          <p v-if="currentSection.description" class="text-muted-foreground">{{ currentSection.description }}</p>
        </div>

        <div v-if="activeMenu === 'dispatch'" class="stat-cards mb-6">
          <Card class="anim-fade-in-up anim-delay-1">
            <CardContent class="p-4">
              <span class="text-sm font-semibold text-muted-foreground">機器人數</span>
              <strong class="stat-number text-foreground block">{{ robots.length }}</strong>
            </CardContent>
          </Card>
          <Card class="anim-fade-in-up anim-delay-2">
            <CardContent class="p-4">
              <span class="text-sm font-semibold text-muted-foreground">待處理任務</span>
              <strong class="stat-number text-foreground block">{{ stats.pending }}</strong>
            </CardContent>
          </Card>
          <Card class="anim-fade-in-up anim-delay-3">
            <CardContent class="p-4">
              <span class="text-sm font-semibold text-muted-foreground">已完成任務</span>
              <strong class="stat-number text-foreground block">{{ stats.completed }}</strong>
            </CardContent>
          </Card>
          <Button class="font-bold w-full h-full text-lg anim-fade-in-up anim-delay-4" @click="openModal('add')">
            <PlusIcon class="size-4" />
            新增任務
          </Button>
        </div>

        <router-view v-slot="{ Component, route: viewRoute }">
          <component
            :is="Component"
            v-bind="viewProps[viewRoute.name]"
            v-on="viewEvents[viewRoute.name] || {}"
          />
        </router-view>
      </main>
    </div>

    <TaskModal v-model="isModalOpen" :title="modalTitle">
      <template v-if="activeModal === 'add'">
        <AssignTaskForm :robots="robots" @assign-task="handleAssignTask" />
      </template>

      <template v-else-if="activeModal === 'cancel'">
        <div class="grid gap-4">
          <p>確定要取消「{{ pendingCancelTask?.title || '此任務' }}」嗎？</p>
          <div class="flex justify-end gap-2">
            <Button variant="outline" @click="closeCancelDialog">取消</Button>
            <Button variant="destructive" @click="cancelTask">確定</Button>
          </div>
        </div>
      </template>

      <template v-else-if="activeModal === 'emergencyStop'">
        <div class="grid gap-4">
          <p class="font-bold text-destructive">⚠️ 確定要對「{{ pendingStopRobot?.name || '此機器人' }}」執行緊急停止嗎？</p>
          <p class="text-muted-foreground text-sm">機器人將立即停止所有動作，進行中的任務將暫停。</p>
          <div class="flex justify-end gap-2">
            <Button variant="outline" @click="closeEmergencyStopDialog">取消</Button>
            <Button variant="destructive" @click="proceedToReconfirm">確定停止</Button>
          </div>
        </div>
      </template>

      <template v-else-if="activeModal === 'emergencyStopReconfirm'">
        <div class="grid gap-4">
          <div class="flex justify-center text-4xl">⚠️</div>
          <p class="font-bold text-destructive text-center">再次確認：即將對「{{ pendingStopRobot?.name || '此機器人' }}」執行緊急停止</p>
          <p class="text-muted-foreground text-sm text-center">此操作無法撤銷，機器人將立即中斷所有進行中的任務。</p>
          <div class="flex justify-end gap-2">
            <Button variant="outline" @click="closeEmergencyStopDialog">取消</Button>
            <Button variant="destructive" @click="confirmEmergencyStop">確認執行緊急停止</Button>
          </div>
        </div>
      </template>

      <template v-else-if="activeModal === 'result'">
        <div class="grid gap-4">
          <p class="text-center text-base text-foreground">{{ confirmMessage }}</p>
          <div class="flex justify-center">
            <Button variant="outline" @click="closeConfirmResult">確認</Button>
          </div>
        </div>
      </template>


      <template v-else-if="activeModal === 'newRobot'">
        <div class="grid gap-4">
          <p class="text-base text-foreground">偵測到新機器人</p>
          <div class="bg-muted rounded-lg p-3">
            <span class="text-sm text-muted-foreground">ROS 名稱：</span>
            <span class="font-mono font-bold">{{ pendingRobotRosName }}</span>
          </div>
          <div class="grid gap-2">
            <label class="text-sm font-semibold text-foreground">顯示名稱</label>
            <Input v-model="pendingRobotName" :placeholder="pendingRobotRosName" @keyup.enter="handleConfirmNewRobot" />
          </div>
          <div class="flex justify-end gap-2">
            <Button variant="outline" @click="dismissPendingRobot">略過</Button>
            <Button @click="handleConfirmNewRobot">確認新增</Button>
          </div>
        </div>
      </template>

      <template v-else-if="activeModal === 'alertDetail' && selectedAlert">
        <AlertDetailDialog
          :alert="selectedAlert"
          :task="selectedAlertTask"
          :alert-source-label="alertSourceLabel"
          :robot-name-map="robotNameMap"
          @close="closeAlertDetail"
        />
      </template>
    </TaskModal>

    <ToastNotification :toasts="toastQueue" @dismiss="dismissToast" />
  </div>
</template>

<style scoped>
.navbar-top {
  height: 56px;
  z-index: 100;
}

.navbar-toggle-btn {
  width: 2.2rem;
  height: 2.2rem;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.system-status--connected {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
}

.system-status--connecting {
  background: #fffbeb;
  border: 1px solid #fde68a;
}

.system-status--disconnected {
  background: #fef2f2;
  border: 1px solid #fecaca;
}

.status-dot-pulse {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}

.status-dot--connected {
  background: #22c55e;
  animation: pulse-dot 2s ease-in-out infinite;
}

.status-dot--connecting {
  background: #f59e0b;
  animation: pulse-dot 1s ease-in-out infinite;
}

.status-dot--disconnected {
  background: #ef4444;
  animation: none;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.sidebar-overlay {
  display: none;
}

.sidebar {
  width: 260px;
  overflow-y: auto;
  flex-shrink: 0;
  transition: width 0.25s ease, padding 0.25s ease;
}

.sidebar--collapsed {
  width: 0;
  padding: 0 !important;
  overflow: hidden;
  border-right: none !important;
}

.menu-item {
  padding: 0.7rem 0.85rem;
  border-radius: 0.75rem;
  color: #64748b;
  transition: background 0.18s ease, color 0.18s ease;
  border: 1px solid transparent;
  background: transparent;
  cursor: pointer;
}

.menu-item:hover {
  background: #f1f5f9;
  color: #1e293b;
}

.menu-item--active {
  background: #f1f5f9;
  color: #0f172a;
  border-color: #e2e8f0;
}

.menu-item--active:hover {
  background: #e2e8f0;
}

.menu-item--active span {
  color: #0f172a;
  font-weight: 800;
}

.dashboard {
  background: var(--color-muted);
}

.stat-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.5rem;
}

.stat-number {
  font-size: 1.875rem;
  line-height: 2.25rem;
}

@media (max-width: 640px) {
  .stat-cards {
    grid-template-columns: 1fr;
  }

  .stat-number {
    font-size: 1.5rem;
    line-height: 2rem;
  }
}

@media (max-width: 1024px) {
  .sidebar-overlay {
    display: block;
    position: fixed;
    inset: 0;
    top: 56px;
    background: rgba(15, 23, 42, 0.35);
    z-index: 80;
  }

  .sidebar {
    position: fixed;
    top: 56px;
    left: 0;
    bottom: 0;
    z-index: 90;
    box-shadow: 4px 0 24px rgba(15, 23, 42, 0.12);
  }

  .sidebar--collapsed {
    box-shadow: none;
  }

  .dashboard {
    padding: 1.25rem !important;
  }
}

@media (max-width: 768px) {
  .navbar-top {
    height: 48px;
    padding: 0 0.75rem !important;
  }

  .sidebar-overlay {
    top: 48px;
  }

  .sidebar {
    top: 48px;
  }

  .dashboard {
    padding: 1rem 0.75rem !important;
  }
}

@media (max-width: 480px) {
  .dashboard {
    padding: 0.75rem 0.5rem !important;
  }
}
</style>

