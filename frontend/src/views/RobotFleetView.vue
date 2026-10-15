<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { BatteryCharging, ChevronDown, Plus, Search } from '@lucide/vue'
import { fleetStore } from '@/stores/demoFleetStore.js'
import { i18n } from '@/i18n/index.js'
import { robotStateLabels } from '@/data/robotStatus.js'
import { clinicFloorOptions } from '@/data/clinicOverviewData.js'
import { normalizeFloor } from '@/data/overviewStatusData.js'
import { chargingCommandAdapter } from '@/services/chargingCommandAdapter.js'
import BatteryGauge from '@/components/robot-status/BatteryGauge.vue'
import TemperatureGauge from '@/components/robot-status/TemperatureGauge.vue'
import TaskAccuracyGauge from '@/components/robot-status/TaskAccuracyGauge.vue'
import ChargingRoutePlane from '@/components/robot-status/ChargingRoutePlane.vue'
import RobotViewport from '@/components/robot-status/RobotViewport.vue'
import '@/styles/robotHmi.css'

const agibotImage = `${import.meta.env.BASE_URL}images/agibot-a2d-transparent.png`

const emit = defineEmits(['edit-robot', 'add-robot'])
const actionNotice = ref('')
const openSections = reactive({ overview: true, task: true, location: false, communication: false, movement: false, diagnostics: false })
const robots = fleetStore.robots
const tasks = fleetStore.tasks
const selectedId = ref(robots.value[0]?.id)
const search = ref(''), selectedFloor = ref('all'), routeVisible = ref(false), stageReady = ref(false)
const floorForRobot = entry => normalizeFloor(entry.floorId ?? entry.floor ?? entry.location?.level_name)
const floorTabs = computed(() => [
  ...[...clinicFloorOptions].sort((a, b) => a.id === 'all' ? -1 : b.id === 'all' ? 1 : a.id - b.id).map(option => ({ id: option.id === 'all' ? 'all' : `floor${option.id}`, label: option.id === 'all' ? 'All' : `${option.id}F`, count: option.id === 'all' ? robots.value.length : robots.value.filter(entry => floorForRobot(entry) === `floor${option.id}`).length })),
  ...(robots.value.some(entry => !floorForRobot(entry)) ? [{ id: 'unassigned', label: '未指定', count: robots.value.filter(entry => !floorForRobot(entry)).length }] : []),
])
const robot = computed(() => robots.value.find(entry => entry.id === selectedId.value) || robots.value[0])
const filteredRobots = computed(() => { const query = search.value.trim().toLocaleLowerCase(); return robots.value.filter(entry => {
  const floor = floorForRobot(entry)
  if (selectedFloor.value !== 'all' && (selectedFloor.value === 'unassigned' ? floor !== null : floor !== selectedFloor.value)) return false
  return !query || `${entry.name} ${entry.id} ${entry.state} ${robotStateLabels[entry.state]} ${i18n.global.getLocaleMessage('en').legacy?.[robotStateLabels[entry.state]] || ''}`.toLocaleLowerCase().includes(query)
}) })
watch(filteredRobots, entries => { if (entries.length && !entries.some(entry => entry.id === selectedId.value)) selectedId.value = entries[0].id })
const charging = computed(() => robot.value?.state === 'charging')
const temperature = computed(() => robot.value?.temperatureSource === 'demo' && !import.meta.env.DEV ? null : robot.value?.motorTemperature ?? null)
const task = computed(() => fleetStore.tasks.value.find(entry => entry.robotId === robot.value?.id && entry.status === 'executing'))
const queued = computed(() => fleetStore.tasks.value.filter(entry => entry.robotId === robot.value?.id && entry.status === 'scheduled').length)
const connection = computed(() => ({ connected: 'Online', connecting: '連線中', disconnected: '尚未連線' }[robot.value?.connectionState] || '尚未連線'))
function selectRobot(id) {
  if (id === selectedId.value) return
  selectedId.value = id
}
</script>

<template>
  <section v-if="robot" class="robot-hmi" :class="{ 'stage-ready': stageReady }" aria-label="機器人狀態控制中心">
    <div class="robot-status-background" aria-hidden="true"></div>
    <aside class="robot-control-panel robot-left-hmi" aria-label="機器人清單">
      <label class="robot-search"><Search :size="15" aria-hidden="true"/><input v-model="search" type="search" aria-label="搜尋機器人" placeholder="搜尋機器人"></label>
      <div class="robot-floor-filter" role="group" aria-label="樓層篩選">
        <button v-for="floor in floorTabs" :key="floor.id" type="button" :aria-pressed="selectedFloor === floor.id" :class="{ 'is-active': selectedFloor === floor.id }" @click="selectedFloor = floor.id">{{ floor.label }}<span>{{ floor.count }}</span></button>
      </div>
      <div class="robot-picker" role="listbox" aria-label="機器人清單">
        <button v-for="(entry, index) in filteredRobots" :key="entry.id" class="robot-list-item" role="option" :aria-selected="entry.id === robot.id" :class="{ 'is-active': entry.id === robot.id }" :style="{ '--robot-index': index }" @click="selectRobot(entry.id)">
          <img class="robot-list-item__avatar" :src="agibotImage" :alt="`${entry.name} AGIBOT A2D 縮圖`">
          <span class="robot-picker__identity"><strong>{{ entry.name }}</strong><small>{{ entry.id }} · {{ robotStateLabels[entry.state] }}</small><small>{{ entry.currentLocation || '位置尚未提供' }}</small></span>
          <span class="robot-list-item__battery"><strong>{{ entry.battery }}%</strong><i><span :style="{ width: `${entry.battery}%` }"></span></i></span>
        </button>
        <p v-if="!filteredRobots.length" class="robot-picker__empty">找不到符合的機器人</p>
      </div>
      <footer class="robot-sidebar-actions"><button type="button" @click="emit('edit-robot', robot.id); actionNotice = '編輯服務尚未接入'">Edit</button><button type="button" class="add-robot" @click="emit('add-robot'); actionNotice = '新增服務尚未接入'"><Plus :size="14"/>Add Robot</button></footer>
      <p v-if="actionNotice" class="robot-action-notice" role="status">{{ actionNotice }}</p>
    </aside>
    <main class="robot-digital-twin-stage">
      <header class="robot-stage-status"><div><strong class="robot-stage-status__name">{{ robot.name }}</strong><span><i :data-state="robot.state"></i>{{ robotStateLabels[robot.state] }}</span></div><p>AGIBOT A2D · {{ robot.currentLocation || '位置尚未提供' }}</p></header>
      <div class="robot-model-cell">
        <RobotViewport :robot-id="robot.id" @ready="stageReady = true"/>
        <ChargingRoutePlane v-if="routeVisible" :waypoint="robot.currentWaypoint" :target="robot.chargingWaypoint"/>
      </div>
    </main>
    <aside class="robot-inspector" aria-label="機器人 Inspector">
      <div class="robot-side-metrics">
        <BatteryGauge :value="robot.battery" :charging="charging" :status="robot.state === 'charging' ? 'Charging' : robot.state === 'idle' ? 'Idle' : null" :runtime="robot.estimatedAvailableTime" :active="stageReady"/>
        <TemperatureGauge :value="temperature" :active="stageReady"/>
      </div>
      <div class="robot-inspector-content">
        <details class="robot-accordion" data-section="overview" :open="openSections.overview" @toggle="openSections.overview = $event.target.open">
          <summary><span>概況<small>{{ robot.name }}</small></span><ChevronDown :size="16" aria-hidden="true"/></summary>
          <div class="accordion-body">
          <header class="inspector-heading"><small>ROBOT OVERVIEW</small><h2 id="overview-heading">{{ robot.name }}</h2><p><i :data-state="robot.state"></i>{{ robotStateLabels[robot.state] }} · {{ connection }}</p></header>
</div>
        </details>
        <details class="robot-accordion" data-section="task" :open="openSections.task" @toggle="openSections.task = $event.target.open">
          <summary><span>目前任務<small>{{ task?.title || '等待指派' }}</small></span><ChevronDown :size="16" aria-hidden="true"/></summary>
          <div class="accordion-body">          <article class="task-brief"><span>目前任務</span><strong>{{ task?.title || '等待指派' }}</strong><p>{{ task ? `${task.origin} → ${task.destination}` : '目前沒有執行中的任務' }}</p><div v-if="task?.progress != null" class="task-progress"><span :style="{ width: `${task.progress}%` }"></span></div><footer><span>{{ task?.progress == null ? '尚無進度' : `${task.progress}%` }}</span><span>等待 {{ queued }} 項</span></footer></article>
</div>
        </details>
        <details class="robot-accordion" data-section="location" :open="openSections.location" @toggle="openSections.location = $event.target.open">
          <summary><span>當前位置<small>{{ robot.currentLocation || '位置尚未提供' }}</small></span><ChevronDown :size="16" aria-hidden="true"/></summary>
          <div class="accordion-body"><div class="status-facts"><article><small>當前位置</small><strong>{{ robot.currentLocation || '位置尚未提供' }}</strong></article><article><small>資料更新</small><strong>{{ robot.lastHeartbeatAt || '尚未提供' }}</strong></article></div></div>
        </details>
        <details class="robot-accordion" data-section="communication" :open="openSections.communication" @toggle="openSections.communication = $event.target.open">
          <summary><span>通訊狀態<small>{{ connection }}</small></span><ChevronDown :size="16" aria-hidden="true"/></summary>
          <div class="accordion-body"><div class="status-facts"><article><small>通訊狀態</small><strong>{{ connection }}</strong></article><article><small>ROS Namespace</small><strong>{{ robot.rosNamespace }}</strong></article><article><small>資料更新</small><strong>{{ robot.lastHeartbeatAt || '尚未提供' }}</strong></article></div></div>
        </details>
        <details class="robot-accordion" data-section="movement" :open="openSections.movement" @toggle="openSections.movement = $event.target.open">
          <summary><span>移動<small>{{ task ? '任務路線進行中' : '沒有執行中的路線' }}</small></span><ChevronDown :size="16" aria-hidden="true"/></summary>
          <div class="accordion-body">
          <header class="inspector-heading"><small>MOTION</small><h2 id="movement-heading">移動</h2><p>{{ task ? '任務路線進行中' : '沒有執行中的路線' }}</p></header>
          <article class="speed-visual"><div class="speed-arc"><span></span><i></i></div><small>CURRENT SPEED</small><h3>尚未提供即時速度</h3><p>最大速度 {{ robot.maxSpeedMps == null ? '尚未提供' : `${robot.maxSpeedMps} m/s` }}</p></article>
          <article class="speed-history"><header><span>最近 30 秒</span><small>EMPTY STATE</small></header><div>尚未提供速度時間序列</div></article>
          <div class="movement-facts"><p><small>移動階段</small><strong>尚未提供</strong></p><p><small>移動方向</small><strong>{{ task?.direction === 'return' ? '返程' : task ? '去程' : '停止' }}</strong></p><p><small>路線進度</small><strong>{{ task?.progress == null ? '尚無資料' : `${task.progress}%` }}</strong></p><p><small>充電任務</small><strong>{{ charging ? '充電中' : '尚未派遣' }}</strong></p></div>
          <button class="charge-button" disabled><BatteryCharging :size="18"/>前往充電</button><p class="service-state">{{ chargingCommandAdapter.unavailableReason }}</p><button class="inspector-action" :aria-pressed="routeVisible" @click="routeVisible = !routeVisible">{{ routeVisible ? '隱藏充電路線' : '預覽充電路線' }}</button>
        </div>
        </details>
        <details class="robot-accordion" data-section="diagnostics" :open="openSections.diagnostics" @toggle="openSections.diagnostics = $event.target.open">
          <summary><span>診斷<small>任務準確率</small></span><ChevronDown :size="16" aria-hidden="true"/></summary>
          <div class="accordion-body">
          <header class="inspector-heading"><small>SYSTEM</small><h2 id="diagnostics-heading">診斷</h2><p><i :data-state="robot.connectionState === 'connected' ? 'idle' : 'offline'"></i>{{ connection }}</p></header>
          <div class="diagnostic-list"><article><small>Fleet</small><strong>{{ robot.fleetName }}</strong></article><article><small>ROS Namespace</small><strong>{{ robot.rosNamespace }}</strong></article><article><small>Navigation Graph</small><strong>{{ robot.navGraphIndex == null ? '尚未提供' : `Graph ${robot.navGraphIndex}` }}</strong></article><article><small>通訊狀態</small><strong>{{ connection }}</strong></article><article><small>系統警告</small><strong>{{ robot.warnings?.length ? robot.warnings.join('、') : '目前沒有警告' }}</strong></article></div>
        <TaskAccuracyGauge :tasks="tasks" :robot-id="robot.id" :active="stageReady && openSections.diagnostics"/></div>
        </details>
      </div>
    </aside>
  </section>
  <section v-else class="robot-hmi">尚無機器人資料</section>
</template>
