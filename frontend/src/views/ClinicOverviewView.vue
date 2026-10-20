<script setup>
import { ArrowUpRight } from '@lucide/vue'
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'
import ClinicOverviewScene from '@/components/scene/ClinicOverviewScene.vue'
import F1SpeedGauge from '@/components/overview/F1SpeedGauge.vue'
import FloorSelector from '@/components/overview/FloorSelector.vue'
import OverviewCalendar from '@/components/overview/OverviewCalendar.vue'
import { useOverviewBatteryHistory } from '@/composables/useOverviewBatteryHistory.js'
import NetworkStatusPanel from '@/components/overview/NetworkStatusPanel.vue'
import RobotConnectionPanel from '@/components/overview/RobotConnectionPanel.vue'
import BuildingTrendPanel from '@/components/overview/BuildingTrendPanel.vue'
import FloorRobotStatusPanel from '@/components/overview/FloorRobotStatusPanel.vue'
import { buildingBatteryHistory, createFloorRobotStatus, normalizeFloor } from '@/data/overviewStatusData.js'
import TaskProgressTimeline from '@/components/overview/TaskProgressTimeline.vue'
import { completionByFloor, createClinicDailySchedules, taskProgressByRobot } from '@/data/clinicOverviewData.js'
import {
  cloneDefaultOverviewCameraPreset,
  cloneDefaultOverviewModelPreset,
  readOverviewCameraPreset,
  readOverviewModelPreset,
  storeOverviewCameraPreset,
  storeOverviewModelPreset,
} from '@/three/clinicOverviewPresets.js'

const props = defineProps({ data: { type: Object, required: true }, theme: { type: String, default: 'light' }, networkStatus: { type: String, default: null } })
const params = new URLSearchParams(window.location.search)
const cameraDebugEnabled = params.get('cameraDebug') === '1'
const modelDebugEnabled = params.get('modelDebug') === '1'
const debugEnabled = cameraDebugEnabled || modelDebugEnabled
const sceneRef = ref(null)
const completionPanel = ref(null)
const toggleCompletionFullscreen = () => {
  if (document.fullscreenElement === completionPanel.value) document.exitFullscreen?.()
  else completionPanel.value?.requestFullscreen?.()
}
const activeFloor = ref('all')
const bottomPanelMode = computed(() => activeFloor.value === 'all' ? 'building-trend' : 'floor-realtime')
const selectedFloorId = computed(() => normalizeFloor(activeFloor.value))
const floorRobotStatus = computed(() => createFloorRobotStatus(props.data.robots, props.data.taskList, props.data.mode === 'demo'))
const rollingHistory = useOverviewBatteryHistory(floorRobotStatus)
const batteryHistory = computed(() => props.data.batteryHistory ?? (props.data.mode === 'demo' ? buildingBatteryHistory : {}))
const floorAnchors = ref({})
const interactionTarget = ref(modelDebugEnabled && !cameraDebugEnabled ? 'model' : 'camera')
const selectedCompletion = computed(() => completionByFloor[String(activeFloor.value)])

const buildingCompletion = computed(() => {
  const completed = completionByFloor.all.reduce((sum, floor) => sum + floor.completed, 0)
  const total = completionByFloor.all.reduce((sum, floor) => sum + floor.total, 0)
  return { completed, total, percentage: total ? Math.round(completed / total * 100) : 0 }
})
const gaugeCompletion = computed(() => activeFloor.value === 'all' ? buildingCompletion.value : selectedCompletion.value)

const dailySchedules = createClinicDailySchedules()
const selectedDate = ref(dailySchedules.find((date) => date.today)?.key || dailySchedules[0].key)
const selectedRobot = ref('robot01')

const modelPreset = reactive(readOverviewModelPreset() || cloneDefaultOverviewModelPreset())
const initialModelPreset = JSON.parse(JSON.stringify(modelPreset))
const cameraPreset = reactive(readOverviewCameraPreset() || cloneDefaultOverviewCameraPreset())
const copyStatus = ref('')
let modelSaveTimer
let copyStatusTimer

const setCameraState = (preset) => {
  if (activeFloor.value !== 'all') return
  Object.assign(cameraPreset.position, preset.position)
  Object.assign(cameraPreset.target, preset.target)
}
const combinedPreset = () => ({
  model: {
    positionX: Number(modelPreset.position.x), positionY: Number(modelPreset.position.y), positionZ: Number(modelPreset.position.z),
    scale: Number(modelPreset.scale), rotationY: Number(modelPreset.rotation.y),
  },
  camera: { position: { ...cameraPreset.position }, target: { ...cameraPreset.target } },
})
const persistAndLogPreset = () => {
  try { storeOverviewCameraPreset(cameraPreset); storeOverviewModelPreset(modelPreset) } catch { /* Browser storage is optional. */ }
  console.info('[Overview preset]', JSON.stringify(combinedPreset(), null, 2))
}
const saveCameraPreset = (preset = cameraPreset) => {
  setCameraState(preset)
  persistAndLogPreset()
}
const scheduleModelSave = () => {
  if (!modelDebugEnabled) return
  clearTimeout(modelSaveTimer)
  modelSaveTimer = window.setTimeout(() => {
    persistAndLogPreset()
  }, 280)
}
watch(modelPreset, scheduleModelSave, { deep: true })

const applyModelPreset = (preset) => {
  Object.assign(modelPreset.position, preset.position)
  Object.assign(modelPreset.rotation, preset.rotation)
  modelPreset.scale = preset.scale
}
const resetCameraPreset = () => { activeFloor.value = 'all'; setCameraState(cloneDefaultOverviewCameraPreset()); persistAndLogPreset(); showStatus('相機已重設') }
watch(activeFloor, floor => { if (floor === 'all') applyModelPreset(initialModelPreset) })
const resetModelPreset = () => { activeFloor.value = 'all'; sceneRef.value?.resetModel(); applyModelPreset(initialModelPreset); showStatus('模型已重設') }
const showStatus = (message) => {
  copyStatus.value = message
  clearTimeout(copyStatusTimer)
  copyStatusTimer = window.setTimeout(() => { copyStatus.value = '' }, 1500)
}
const copyActivePreset = async () => {
  try { await navigator.clipboard.writeText(JSON.stringify(combinedPreset(), null, 2)); showStatus('已複製') }
  catch { showStatus('無法存取剪貼簿') }
}
const savePreset = () => { persistAndLogPreset(); showStatus('已保存') }
onBeforeUnmount(() => { clearTimeout(modelSaveTimer); clearTimeout(copyStatusTimer) })
</script>

<template>
  <section class="clinic-overview-dashboard" aria-label="診所營運總覽">
    <div class="clinic-building-stage">
      <ClinicOverviewScene ref="sceneRef" :active-floor="activeFloor" :theme="theme" :camera-debug="cameraDebugEnabled" :model-debug="modelDebugEnabled" :interaction-target="interactionTarget" :camera-preset="cameraPreset" :model-preset="modelPreset" @update:model-preset="applyModelPreset" @camera-change="setCameraState" @camera-preset-change="saveCameraPreset" @model-interaction-end="scheduleModelSave" @floor-anchors="floorAnchors = $event" />
    </div>

    <aside ref="completionPanel" class="completion-panel completion-border-shell overview-tool-panel dashboard-panel-enter">
      <div class="completion-panel-content">
        <header class="completion-header"><h2>今日完成率</h2><button class="completion-expand" type="button" aria-label="切換今日完成率全螢幕" title="全螢幕" @click="toggleCompletionFullscreen"><ArrowUpRight :size="16" :stroke-width="1.5" /></button></header>
        <F1SpeedGauge :value="gaugeCompletion.percentage" :label="activeFloor === 'all' ? '全棟完成率' : selectedCompletion.label" />
        <div v-if="activeFloor === 'all'" class="completion-summary">
          <div v-for="floor in selectedCompletion" :key="floor.id"><span>{{ floor.label }}</span><strong>{{ floor.percentage }}%</strong></div>
        </div>
        <div v-else class="completion-summary floor-task-summary">
          <div><span>{{ selectedCompletion.label }}</span><strong>{{ selectedCompletion.percentage }}%</strong></div>
          <div><span>完成 / 總任務</span><strong>{{ selectedCompletion.completed }} / {{ selectedCompletion.total }}</strong></div>
        </div>
      </div>
    </aside>

    <FloorSelector v-model="activeFloor" class="clinic-floor-control" :anchors="floorAnchors" />

    <div class="right-information-stack">
      <OverviewCalendar v-model="selectedDate" :dates="dailySchedules" />
      <TaskProgressTimeline v-model="selectedRobot" :progress-by-robot="taskProgressByRobot" />
    </div>

    <aside class="clinic-robot-status bottom-status-panel dashboard-panel-enter" :data-mode="bottomPanelMode">
      <div v-if="bottomPanelMode === 'building-trend'" class="overview-connectivity">
        <NetworkStatusPanel :status="networkStatus" />
        <RobotConnectionPanel :robots="data.robots" />
      </div>
      <div class="overview-bottom-main overview-tool-panel">
      <Transition name="bottom-panel-switch" mode="out-in">
        <BuildingTrendPanel v-if="bottomPanelMode === 'building-trend'" key="building-trend" :history="batteryHistory" :source="data.batteryHistory ? '歷史資料' : data.mode === 'demo' ? '展示資料' : '尚無歷史資料'" />
        <FloorRobotStatusPanel v-else :key="selectedFloorId" :floor="selectedFloorId" :history="data.batteryHistory?.[selectedFloorId] || []" :rolling-history="rollingHistory[selectedFloorId]" :robots="floorRobotStatus[selectedFloorId]" :demo="data.mode === 'demo'" />
      </Transition>
      </div>
    </aside>

    <aside v-if="debugEnabled" class="overview-debug-panel">
      <header><strong>Overview 調整</strong><span>{{ copyStatus }}</span></header>
      <div v-if="cameraDebugEnabled && modelDebugEnabled" class="debug-target-switch"><button type="button" :class="{ active: interactionTarget === 'camera' }" @click="interactionTarget = 'camera'">操作相機</button><button type="button" :class="{ active: interactionTarget === 'model' }" @click="interactionTarget = 'model'">操作模型</button></div>
      <p>{{ interactionTarget === 'camera' ? '拖曳旋轉 · 右鍵平移 · 滾輪縮放' : '拖曳平移 · Shift 拖曳高度 · Alt＋左鍵或右鍵旋轉 · 滾輪縮放' }}</p>
      <footer><button type="button" @click="copyActivePreset">Copy preset</button><button type="button" @click="resetModelPreset">Reset model</button><button type="button" @click="resetCameraPreset">Reset camera</button><button type="button" @click="savePreset">Save preset</button></footer>
    </aside>
  </section>
</template>

<style scoped>
@property --completion-border-angle{syntax:'<angle>';inherits:false;initial-value:0deg}
.clinic-overview-dashboard{--overview-text:var(--text-primary);--overview-muted:var(--text-secondary);--overview-border:var(--info-divider);--overview-divider:var(--info-divider);--overview-orange:var(--overview-accent-text);--overview-rail-width:clamp(310px,22vw,350px);position:absolute;z-index:3;inset:0;height:100%;min-height:0;overflow:hidden;background:transparent;color:var(--overview-text);font-size:var(--font-body);line-height:1.35}
.clinic-building-stage{position:absolute;inset:0;background:transparent}
.completion-panel{--panel-delay:100ms;position:absolute;z-index:6;isolation:isolate;top:142px;left:22px;width:298px;height:286px;background:var(--overview-completion-background);backdrop-filter:var(--overview-completion-backdrop);-webkit-backdrop-filter:var(--overview-completion-backdrop);border-radius:4px;padding:12px 22px 20px;overflow:hidden;color:var(--text-primary)}.completion-border-shell::before{display:none}.completion-panel-content{position:relative;z-index:1;display:grid;width:100%;height:100%;grid-template-rows:26px 164px 42px;row-gap:8px;align-content:start;justify-items:center}@keyframes completion-border-flow{to{--completion-border-angle:360deg}}@keyframes completion-glass-shimmer{0%,20%{opacity:0;transform:translateX(-38%) rotate(4deg)}38%{opacity:.8}64%{opacity:.42}84%,100%{opacity:0;transform:translateX(38%) rotate(4deg)}}
.completion-panel,.bottom-status-panel{animation-fill-mode:backwards}
.completion-header h2{display:flex;align-items:center;gap:7px}.completion-header h2 svg{color:var(--theme-primary)}.completion-header{display:flex;width:100%;align-items:center;justify-content:space-between}.completion-header h2{margin:0;color:var(--text-primary);font-size:var(--info-title-size);font-weight:var(--info-title-weight);letter-spacing:var(--info-title-spacing)}.completion-header span{display:flex;align-items:center;gap:5px;color:var(--text-muted);font-size:8px;letter-spacing:.14em}.completion-header i{width:5px;height:5px;background:var(--overview-yellow-text);border-radius:50%;box-shadow:0 0 7px rgba(var(--overview-yellow-rgb),.45);animation:completion-live-pulse 1.8s ease-in-out infinite}.completion-summary{display:grid;grid-template-columns:repeat(3,1fr);width:100%;text-align:center}.completion-summary>div{display:grid;gap:6px;animation:dashboard-fade 300ms ease calc(1300ms + (var(--floor-index,0) * 130ms)) both}.completion-summary>div:nth-child(2){--floor-index:1;border-inline:1px solid var(--overview-divider)}.completion-summary>div:nth-child(3){--floor-index:2}.completion-summary span{color:var(--text-secondary);font-size:11px}.completion-summary strong{color:var(--text-primary);font-size:14px;font-weight:500;font-variant-numeric:tabular-nums}.floor-task-summary{grid-template-columns:repeat(2,1fr)}@keyframes completion-live-pulse{0%,100%{opacity:.42;transform:scale(.82)}50%{opacity:1;transform:scale(1.12)}}
.clinic-floor-control{position:absolute;z-index:5;inset:0}
.right-information-stack{position:absolute;z-index:6;top:78px;right:22px;bottom:18px;display:grid;width:var(--overview-rail-width);min-height:0;grid-template-columns:minmax(0,1fr);grid-template-rows:repeat(2,minmax(0,1fr));gap:14px}
.clinic-robot-status{position:absolute;z-index:6;left:20px;right:calc(var(--overview-rail-width) + 36px);top:auto;bottom:18px;width:auto;height:236px;min-height:0}
.overview-debug-panel{position:absolute;z-index:30;top:76px;left:360px;display:grid;width:348px;gap:10px;padding:13px;color:var(--overview-text);background:var(--info-background);border:var(--info-border);border-radius:var(--info-radius);box-shadow:var(--info-shadow);backdrop-filter:var(--info-backdrop)}.overview-debug-panel header{display:flex;justify-content:space-between;font-size:13px}.overview-debug-panel header span{color:var(--overview-orange);font-size:11px}.debug-target-switch{display:grid;grid-template-columns:1fr 1fr;gap:3px;padding:3px;background:rgba(91,98,94,.08);border-radius:6px}.debug-target-switch button{height:28px;background:transparent;border:0;border-radius:4px;cursor:pointer}.debug-target-switch button.active{background:#fff;box-shadow:0 2px 7px rgba(20,24,28,.08)}fieldset{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin:0;padding:7px;border:1px solid var(--overview-border);border-radius:6px}legend{padding:0 5px;color:var(--overview-muted);font-size:10px}.overview-debug-panel label{display:grid;gap:3px;color:var(--overview-muted);font-size:9px}.overview-debug-panel input{width:100%;height:29px;padding:0 6px;color:var(--overview-text);font-size:11px;background:rgba(255,255,255,.7);border:1px solid var(--overview-border);border-radius:4px}.scale-input{grid-template-columns:50px 1fr;align-items:center}.overview-debug-panel>p{margin:0;color:var(--overview-muted);font-size:10px}.overview-debug-panel footer{display:flex;gap:5px}.overview-debug-panel footer button{flex:1;min-height:29px;padding:4px;color:var(--overview-text);font-size:10px;background:rgba(255,255,255,.7);border:1px solid var(--overview-border);border-radius:4px;cursor:pointer}
.bottom-status-panel{--panel-delay:520ms;isolation:isolate;display:grid;grid-template-columns:minmax(150px,20%) minmax(0,1fr);gap:12px;overflow:visible}.bottom-status-panel[data-mode="floor-realtime"]{grid-template-columns:minmax(0,1fr)}.overview-connectivity{display:grid;grid-template-rows:repeat(2,minmax(0,1fr));gap:12px;min-height:0}.overview-bottom-main{min-width:0;min-height:0;overflow:hidden}.bottom-status-panel>*{position:relative;z-index:1}.bottom-panel-switch-enter-active,.bottom-panel-switch-leave-active{transition:opacity 150ms ease,transform 150ms ease}.bottom-panel-switch-enter-from,.bottom-panel-switch-leave-to{opacity:0;transform:translateY(4px)}
@media(prefers-reduced-motion:reduce){.completion-border-shell::before,.completion-header i{animation:none}.completion-border-shell::before{--completion-border-angle:110deg}}
/* Short screens scroll the dashboard instead of overlapping the completion panel. */
@media(max-height:660px){.clinic-overview-dashboard{overflow-y:auto}.clinic-robot-status{top:444px;bottom:auto;height:240px}.right-information-stack{bottom:auto;height:584px}}
.completion-expand{position:absolute;top:0;right:-10px;display:grid;place-items:center;width:24px;height:24px;padding:0;color:var(--text-secondary);background:transparent;border:0;cursor:pointer;transition:color 160ms ease}.completion-expand:hover,.completion-expand:focus-visible{color:var(--theme-primary)}.completion-expand:focus-visible{outline:1px solid currentColor;outline-offset:2px}
.completion-panel:fullscreen{position:fixed;inset:0;width:100%;height:100%;padding:clamp(20px,5vh,60px);background:var(--info-background);border:0;border-radius:0;overflow:auto}
.completion-panel:fullscreen .completion-panel-content{max-width:720px;margin:auto;grid-template-rows:auto minmax(220px,1fr) auto;gap:24px}
.completion-panel:fullscreen :deep(.f1-speed-gauge){width:100%;max-width:680px;height:100%;max-height:65vh;align-self:center}
@media(max-width:760px){
  .clinic-overview-dashboard{display:flex;flex-direction:column;overflow-y:auto;padding:0 16px 16px}
  .clinic-robot-status{position:relative;inset:auto;order:2;flex:0 0 auto;margin-top:444px;grid-template-columns:minmax(0,1fr);min-height:660px}
  .overview-connectivity{grid-template-columns:repeat(2,minmax(0,1fr));grid-template-rows:140px}
  .overview-bottom-main{min-height:500px}
  .right-information-stack{position:relative;inset:auto;order:3;flex:0 0 600px;width:100%;margin-top:16px}
}
</style>
