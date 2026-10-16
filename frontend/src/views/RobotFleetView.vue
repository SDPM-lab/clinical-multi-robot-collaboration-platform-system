<script setup>
import { computed, ref, watch } from 'vue'
import { Bot, Plus, Search, Wifi, WifiOff, LoaderCircle } from '@lucide/vue'
import { fleetStore } from '@/stores/demoFleetStore.js'
import { i18n, t, translateLocation } from '@/i18n/index.js'
import { robotStateLabels } from '@/data/robotStatus.js'
import { clinicFloorOptions } from '@/data/clinicOverviewData.js'
import { normalizeFloor } from '@/data/overviewStatusData.js'
import { robotSeriesColors } from '@/config/visualTokens.js'
import BatteryGauge from '@/components/robot-status/BatteryGauge.vue'
import TemperatureGauge from '@/components/robot-status/TemperatureGauge.vue'
import RobotViewport from '@/components/robot-status/RobotViewport.vue'
import AddRobotStatusDialog from '@/components/robot-status/AddRobotStatusDialog.vue'
import '@/styles/robotHmi.css'

const agibotImage = `${import.meta.env.BASE_URL}images/agibot-a2d-transparent.png`

const emit = defineEmits(['edit-robot', 'add-robot'])
const actionNotice = ref('')
const robots = fleetStore.robots
const selectedId = ref(robots.value[0]?.id)
const search = ref(''), selectedFloor = ref('all'), stageReady = ref(false), structureAvailable = ref(true), selectedZone = ref(null), viewport = ref(null), addDialogOpen = ref(false)
const floorForRobot = entry => normalizeFloor(entry.floorId ?? entry.floor ?? entry.location?.level_name)
const floorLabel = entry => {
  const floor = floorForRobot(entry)
  return floor ? `${floor.replace('floor', '')}F` : t('robotStatus.unassigned')
}
const floorCode = entry => {
  const floor = floorForRobot(entry)
  return floor ? `F${floor.replace('floor', '')}` : t('robotStatus.unassigned')
}
const floorTabs = computed(() => [
  ...[...clinicFloorOptions].sort((a, b) => a.id === 'all' ? -1 : b.id === 'all' ? 1 : a.id - b.id).map(option => ({ id: option.id === 'all' ? 'all' : `floor${option.id}`, label: option.id === 'all' ? t('robotStatus.all') : `${option.id}F`, count: option.id === 'all' ? robots.value.length : robots.value.filter(entry => floorForRobot(entry) === `floor${option.id}`).length })),
  ...(robots.value.some(entry => !floorForRobot(entry)) ? [{ id: 'unassigned', label: t('robotStatus.unassigned'), count: robots.value.filter(entry => !floorForRobot(entry)).length }] : []),
])
const robot = computed(() => robots.value.find(entry => entry.id === selectedId.value) || robots.value[0])
const filteredRobots = computed(() => { const query = search.value.trim().toLocaleLowerCase(); return robots.value.filter(entry => {
  const floor = floorForRobot(entry)
  if (selectedFloor.value !== 'all' && (selectedFloor.value === 'unassigned' ? floor !== null : floor !== selectedFloor.value)) return false
  return !query || `${entry.name} ${entry.id} ${floorCode(entry)} ${entry.state} ${robotStateLabels[entry.state]} ${i18n.global.getLocaleMessage('en').legacy?.[robotStateLabels[entry.state]] || ''}`.toLocaleLowerCase().includes(query)
}) })
watch(filteredRobots, entries => { if (entries.length && !entries.some(entry => entry.id === selectedId.value)) selectedId.value = entries[0].id })
const temperature = computed(() => robot.value?.temperatureSource === 'demo' && !import.meta.env.DEV ? null : robot.value?.motorTemperature ?? null)
const connectionState = computed(() => ['connected', 'connecting', 'disconnected'].includes(robot.value?.connectionState) ? robot.value.connectionState : 'disconnected')
const connectionIcon = computed(() => connectionState.value === 'connected' ? Wifi : connectionState.value === 'connecting' ? LoaderCircle : WifiOff)
function selectRobot(id) {
  if (id === selectedId.value) return
  const nextRobot = robots.value.find(entry => entry.id === id)
  if (nextRobot?.modelAssetKey !== robot.value?.modelAssetKey) {
    stageReady.value = false
    structureAvailable.value = false
  }
  selectedId.value = id
  selectedZone.value = null
}
function onViewportReady(details) {
  stageReady.value = true
  structureAvailable.value = details?.structureAvailable ?? true
}
function onRobotCreated(created) {
  addDialogOpen.value = false
  search.value = ''
  selectedFloor.value = 'all'
  selectRobot(created.id)
}
function focusZone(zone) {
  if (selectedZone.value === zone) return showWholeRobot()
  selectedZone.value = zone
  viewport.value?.focusZone?.(zone)
}
function showWholeRobot() {
  selectedZone.value = null
  viewport.value?.showWholeRobot?.()
}
</script>

<template>
  <section v-if="robot" class="robot-hmi" :class="{ 'stage-ready': stageReady }" :aria-label="t('nav.robots')">
    <div class="robot-status-background" aria-hidden="true"></div>
    <aside class="robot-control-panel robot-left-hmi" :aria-label="t('robotStatus.list')">
      <label class="robot-search"><Search :size="15" aria-hidden="true"/><input v-model="search" type="search" :aria-label="t('robotStatus.search')" :placeholder="t('robotStatus.search')"></label>
      <div class="robot-floor-filter" role="group" :aria-label="t('robotStatus.floorFilter')">
        <button v-for="floor in floorTabs" :key="floor.id" type="button" :aria-pressed="selectedFloor === floor.id" :class="{ 'is-active': selectedFloor === floor.id }" @click="selectedFloor = floor.id">{{ floor.label }}<span>{{ floor.count }}</span></button>
      </div>
      <div class="robot-picker" role="listbox" :aria-label="t('robotStatus.list')">
        <button v-for="entry in filteredRobots" :key="entry.id" class="robot-list-item" role="option" :aria-selected="entry.id === robot.id" :class="{ 'is-active': entry.id === robot.id }" :style="{ '--battery-color': robotSeriesColors[robots.findIndex(item => item.id === entry.id) % robotSeriesColors.length] }" @click="selectRobot(entry.id)">
          <span v-if="entry.modelAssetKey" class="robot-list-item__avatar robot-list-item__avatar--custom"><Bot :size="29" aria-hidden="true"/></span>
          <img v-else class="robot-list-item__avatar" :src="agibotImage" :alt="`${entry.name} AGIBOT A2D 縮圖`">
          <span class="robot-picker__identity"><strong>{{ entry.name }}</strong><small>{{ t(`robotStatus.states.${entry.state}`) }} · {{ floorCode(entry) }}</small><small>{{ entry.currentLocation ? translateLocation(entry.currentLocation) : t('robotStatus.noLocation') }}</small></span>
          <span class="robot-list-item__battery"><strong>{{ entry.battery }}%</strong><i><span :style="{ width: `${entry.battery}%` }"></span></i></span>
        </button>
        <p v-if="!filteredRobots.length" class="robot-picker__empty">{{ t('robotStatus.noRobots') }}</p>
      </div>
      <footer class="robot-sidebar-actions"><button type="button" @click="emit('edit-robot', robot.id); actionNotice = '編輯服務尚未接入'">{{ t('robotStatus.edit') }}</button><button type="button" class="add-robot" :aria-label="t('robotStatus.addRobot')" :title="t('robotStatus.addRobot')" @click="emit('add-robot'); addDialogOpen = true"><Plus :size="18" aria-hidden="true"/></button></footer>
      <p v-if="actionNotice" class="robot-action-notice" role="status">{{ actionNotice }}</p>
    </aside>
    <main class="robot-digital-twin-stage">
      <header class="robot-stage-status"><div><strong class="robot-stage-status__name">{{ robot.name }}</strong><span><i :data-state="robot.state"></i>{{ t(`robotStatus.states.${robot.state}`) }}</span></div><p>{{ robot.modelAssetKey ? robot.model : 'AGIBOT A2D' }} · {{ robot.currentLocation ? translateLocation(robot.currentLocation) : t('robotStatus.noLocation') }}</p></header>
      <div class="robot-model-cell">
        <RobotViewport ref="viewport" :robot-id="robot.id" :model-asset-key="robot.modelAssetKey" @ready="onViewportReady"/>
      </div>
    </main>
    <aside class="robot-inspector" :aria-label="t('robotStatus.title')">
      <div class="robot-side-metrics">
        <BatteryGauge :value="robot.battery" :active="stageReady"/>
        <TemperatureGauge :value="temperature" :active="stageReady"/>
      </div>
      <section class="robot-inspector-content robot-info-card" aria-labelledby="robot-info-title">
        <header class="robot-info-card__header"><h2 id="robot-info-title">{{ t('robotStatus.title') }}</h2></header>
        <dl class="robot-info-card__facts">
          <div><dt>{{ t('robotStatus.id') }}</dt><dd>{{ robot.id }}</dd></div>
          <div><dt>{{ t('robotStatus.floor') }}</dt><dd>{{ floorLabel(robot) }}</dd></div>
          <div><dt>{{ t('robotStatus.location') }}</dt><dd>{{ robot.currentLocation ? translateLocation(robot.currentLocation) : t('robotStatus.noLocation') }}</dd></div>
          <div><dt>{{ t('robotStatus.connection') }}</dt><dd class="robot-info-card__connection" :data-state="connectionState"><span class="robot-info-card__connection-icon"><component :is="connectionIcon" :size="15" aria-hidden="true"/></span>{{ t(`robotStatus.connectionStates.${connectionState}`) }}</dd></div>
          <div v-if="robot.manufacturer"><dt>{{ t('robotStatus.manufacturer') }}</dt><dd>{{ robot.manufacturer }}</dd></div>
          <div><dt>{{ t('robotStatus.serial') }}</dt><dd>{{ robot.serialNumber || t('robotStatus.noValue') }}</dd></div>
          <div><dt>{{ t('robotStatus.activeTaskId') }}</dt><dd>{{ robot.activeTaskId || t('robotStatus.noValue') }}</dd></div>
        </dl>
        <div v-if="structureAvailable" class="robot-info-card__structure">
          <h3>{{ t('robotStatus.structure') }}</h3>
          <div role="group" :aria-label="t('robotStatus.structure')">
            <button v-for="zone in [{ id: 'l', label: 'leftArm' }, { id: 'r', label: 'rightArm' }, { id: 'head', label: 'head' }, { id: 'base', label: 'base' }]" :key="zone.id" type="button" :disabled="!stageReady" :aria-pressed="selectedZone === zone.id" @click="focusZone(zone.id)">{{ t(`robotStatus.${zone.label}`) }}</button>
            <button type="button" :disabled="!stageReady" :aria-pressed="selectedZone === null" @click="showWholeRobot">{{ t('robotStatus.whole') }}</button>
          </div>
        </div>
      </section>
    </aside>
    <AddRobotStatusDialog v-if="addDialogOpen" @close="addDialogOpen = false" @created="onRobotCreated"/>
  </section>
  <section v-else class="robot-hmi">{{ t('robotStatus.noRobots') }}</section>
</template>
