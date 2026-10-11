<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import TaskScheduleSidebar from '@/components/dispatch/TaskScheduleSidebar.vue'
import TaskForm from '@/components/dispatch/TaskForm.vue'
import DispatchMapScene from '@/components/dispatch/DispatchMapScene.vue'
import { dispatchTaskLocations } from '@/config/dispatchDestinations.js'
import { locale, t, translateTask } from '@/i18n/index.js'
import { demoFleetStore, timeToSeconds } from '@/stores/demoFleetStore.js'

const destination = ref('Nurse Reception')
const origin = ref('Pharmacy')
const selectedDate = ref('2026-08-31')
const activePanel = ref('create')
const panelTopOffset = ref(10)
const activatePanel = async (panel, focus = false) => {
  activePanel.value = panel
  if (focus) { await nextTick(); document.getElementById(`dispatch-${panel}-tab`)?.focus() }
}
const visibleTasks = computed(() => demoFleetStore.tasks.value.filter((task) => (task.date || '2026-08-31') === selectedDate.value))
const selectedRobotId = ref('R01')
const selectionStep = ref(0)
const routeConfirmed = ref(false)
const chosenOrigin = ref(false)
const chosenDestination = ref(false)
const scheduleEditing = ref(false)
const errorMessage = ref('')
const pendingDelete = ref(null)
const cancelDeleteButton = ref(null)
const viewportWidth = ref(window.innerWidth)
const syncViewportWidth = () => { viewportWidth.value = window.innerWidth }
onMounted(() => window.addEventListener('resize', syncViewportWidth))
onBeforeUnmount(() => window.removeEventListener('resize', syncViewportWidth))
const mapInsets = computed(() => ({ left: 0, right: 0, top: 0, bottom: viewportWidth.value >= 1100 ? 150 : 0 }))
const locations = dispatchTaskLocations
const selectMapLocation = (label) => {
  activePanel.value = 'create'
  if (selectionStep.value === 1) {
    destination.value = label
    chosenDestination.value = true
    selectionStep.value = 2
    routeConfirmed.value = true
  } else {
    origin.value = label
    chosenOrigin.value = true
    chosenDestination.value = false
    selectionStep.value = 1
    routeConfirmed.value = false
  }
}
const selectFormLocation = (field, label) => {
  if (field === 'origin') { origin.value = label; chosenOrigin.value = true }
  else { destination.value = label; chosenDestination.value = true }
  routeConfirmed.value = chosenOrigin.value && chosenDestination.value
  selectionStep.value = routeConfirmed.value ? 2 : chosenOrigin.value ? 1 : 0
}
const localizedReason = (reason) => {
  if (locale.value !== 'en') return reason
  if (reason?.includes('時間重疊')) return t('dispatch.timeConflict')
  if (reason?.includes('充電時段衝突')) return t('dispatch.chargingConflict')
  if (reason?.includes('電量不足')) return t('dispatch.lowBattery')
  if (reason?.includes('離線')) return t('dispatch.robotOffline')
  if (reason?.includes('找不到指定機器人')) return t('dispatch.robotNotFound')
  if (reason?.includes('找不到任務')) return t('dispatch.taskNotFound')
  return reason
}
const handleReschedule = (taskId, time) => {
  const result = demoFleetStore.moveTask(taskId, timeToSeconds(time))
  errorMessage.value = result.ok ? t('dispatch.saved') : localizedReason(result.reason)
}
watch(pendingDelete, async (task) => { if (task) { await nextTick(); cancelDeleteButton.value?.focus() } })
const confirmDelete = () => {
  if (!pendingDelete.value) return
  const result = demoFleetStore.deleteTask(pendingDelete.value.id)
  errorMessage.value = result.ok ? t('dispatch.deleted', { id: pendingDelete.value.id }) : localizedReason(result.reason)
  pendingDelete.value = null
}
const handleCreateTask = (payload) => {
  const result = demoFleetStore.createTask(payload)
  errorMessage.value = result.ok ? '' : localizedReason(result.reason)
  if (result.ok) selectedDate.value = payload.date
}
const notification = computed(() => {
  if (errorMessage.value) return errorMessage.value
  const raw = demoFleetStore.notification.value
  if (locale.value !== 'en') return raw
  const created = /^已建立 (T\d+)「(.+)」$/u.exec(raw)
  return created ? t('dispatch.created', { id: created[1], title: translateTask(created[2]) }) : raw
})
</script>

<template>
  <div class="task-dispatch-page">
    <div class="dispatch-workspace">
      <aside class="dispatch-side-panel" :class="{ 'is-schedule': activePanel === 'schedule' }" :style="{ '--panel-top-offset': `${panelTopOffset}px` }">
        <div class="dispatch-panel-tabs" role="tablist" :aria-label="t('dispatch.panelTabs')" @keydown.left.prevent="activatePanel('create', true)" @keydown.right.prevent="activatePanel('schedule', true)">
          <button id="dispatch-create-tab" type="button" role="tab" :aria-selected="activePanel === 'create'" aria-controls="dispatch-create-panel" :tabindex="activePanel === 'create' ? 0 : -1" @click="activatePanel('create')">{{ t('dispatchForm.title') }}</button>
          <button id="dispatch-schedule-tab" type="button" role="tab" :aria-selected="activePanel === 'schedule'" aria-controls="dispatch-schedule-panel" :tabindex="activePanel === 'schedule' ? 0 : -1" @click="activatePanel('schedule')">{{ t('dispatch.scheduleTab') }}</button>
        </div>
        <div v-show="activePanel === 'create'" id="dispatch-create-panel" class="dispatch-panel-body" role="tabpanel" aria-labelledby="dispatch-create-tab">
          <TaskForm :destination="destination" :origin="origin" v-model:robot-id="selectedRobotId" :date="selectedDate" :robots="demoFleetStore.robots.value" :locations="locations" @update:origin="selectFormLocation('origin', $event)" @update:destination="selectFormLocation('destination', $event)" @submit="handleCreateTask" />
        </div>
        <div v-show="activePanel === 'schedule'" id="dispatch-schedule-panel" class="dispatch-panel-body" role="tabpanel" aria-labelledby="dispatch-schedule-tab">
          <TaskScheduleSidebar v-model:date="selectedDate" :editing="scheduleEditing" :robots="demoFleetStore.robots.value" :tasks="visibleTasks" @edit="scheduleEditing = !scheduleEditing" @reschedule="handleReschedule" @request-delete="pendingDelete = $event" />
        </div>
      </aside>
      <DispatchMapScene class="dispatch-map" :robots="demoFleetStore.robots.value" :robot-id="selectedRobotId" :origin="origin" :destination="destination" :selection-step="selectionStep" :route-confirmed="routeConfirmed" :allowed-locations="locations" :viewport-insets="mapInsets" @select-location="selectMapLocation" @visual-top-change="panelTopOffset = $event" />
    </div>
    <div v-if="pendingDelete" class="dispatch-confirm-backdrop" @click.self="pendingDelete=null" @keydown.esc="pendingDelete=null">
      <section class="dispatch-confirm" role="alertdialog" aria-modal="true" aria-labelledby="dispatch-delete-title" aria-describedby="dispatch-delete-message">
        <h2 id="dispatch-delete-title">{{ t('dispatch.deleteTitle') }}</h2>
        <p id="dispatch-delete-message">{{ t('dispatch.deleteMessage', { id: pendingDelete.id, title: translateTask(pendingDelete.title) }) }}</p>
        <div class="dispatch-confirm-actions"><button ref="cancelDeleteButton" type="button" @click="pendingDelete=null">{{ t('dispatch.cancel') }}</button><button type="button" class="is-danger" @click="confirmDelete">{{ t('dispatch.delete') }}</button></div>
      </section>
    </div>
    <Transition name="dispatch-toast"><div v-if="notification" class="dispatch-toast" role="status">{{ notification }}<button type="button" aria-label="關閉通知" @click="errorMessage=''">×</button></div></Transition>
  </div>
</template>

<style scoped>
.task-dispatch-page{--dispatch-accent:#FB9966;position:absolute;inset:0;box-sizing:border-box;width:100%;height:100dvh;padding-top:64px;overflow:hidden;color:var(--text-primary)}
.dispatch-workspace{display:grid;grid-template-columns:clamp(400px,29vw,460px) minmax(0,1fr);gap:14px;position:relative;box-sizing:border-box;width:100%;height:100%;min-height:0;padding:6px 24px 12px;container-type:inline-size}.dispatch-map{grid-column:2;grid-row:1;position:relative;min-width:0;min-height:0}.dispatch-side-panel{z-index:10;grid-column:1;grid-row:1;display:grid;grid-template-rows:45px minmax(0,1fr);align-self:start;box-sizing:border-box;width:100%;height:min(calc(100% - var(--panel-top-offset, 10px)),550px);margin-top:var(--panel-top-offset, 10px);min-height:0;overflow:hidden;background:rgba(247,249,250,.54);border:1px solid rgba(255,255,255,.68);border-radius:16px;box-shadow:0 18px 52px #34433820;backdrop-filter:blur(24px) saturate(115%);-webkit-backdrop-filter:blur(24px) saturate(115%)}.dispatch-side-panel.is-schedule{height:calc(100% - var(--panel-top-offset, 10px))}:global([data-theme='dark']) .dispatch-side-panel{background:rgba(34,42,47,.58);border-color:rgba(255,255,255,.16)}.dispatch-panel-tabs{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:5px;padding:7px 9px 0;border-bottom:1px solid var(--glass-divider)}.dispatch-panel-tabs button{min-width:0;padding:0 8px;color:var(--text-secondary);background:transparent;border:0;border-bottom:2px solid transparent;border-radius:8px 8px 0 0;font:inherit;font-size:15px;font-weight:550;cursor:pointer}.dispatch-panel-tabs button:hover{background:color-mix(in srgb,var(--theme-primary) 8%,transparent)}.dispatch-panel-tabs button[aria-selected=true]{color:var(--text-primary);background:color-mix(in srgb,#fb9966 10%,transparent);border-bottom-color:#fb9966;font-weight:650}.dispatch-panel-tabs button:focus-visible{outline:2px solid var(--theme-primary);outline-offset:-2px}.dispatch-panel-body{min-width:0;min-height:0}.dispatch-panel-body :deep(.task-panel){background:transparent;border:0;border-radius:0;box-shadow:none;backdrop-filter:none;-webkit-backdrop-filter:none}.dispatch-panel-body :deep(.task-panel > header){display:none}.dispatch-panel-body :deep(.schedule-header h2){display:none}.dispatch-panel-body :deep(.schedule-header){justify-content:flex-end;padding-top:8px;padding-bottom:5px}.dispatch-panel-body :deep(.schedule-list){padding-bottom:14px}
.dispatch-toast{position:fixed;z-index:80;right:28px;top:78px;max-width:360px;padding:12px 16px;color:var(--text-primary);font-size:13px;background:var(--panel-bg-strong);border:1px solid var(--panel-border);border-radius:8px;box-shadow:var(--dropdown-shadow)}.dispatch-toast button{margin-left:12px;border:0;background:none;color:inherit;cursor:pointer}.dispatch-toast-enter-active,.dispatch-toast-leave-active{transition:opacity .2s}.dispatch-toast-enter-from,.dispatch-toast-leave-to{opacity:0}
@media(max-width:1099px){.task-dispatch-page{inset:64px 0 0;height:auto;padding-top:0;overflow-y:auto}.dispatch-workspace{grid-template-columns:minmax(0,1fr);grid-template-rows:auto minmax(520px,65vh);height:auto;min-height:100%;padding:8px 12px 12px;gap:12px}.dispatch-side-panel{grid-column:1;grid-row:1;width:min(100%,520px);height:530px;margin-top:0}.dispatch-side-panel.is-schedule{height:620px}.dispatch-map{grid-column:1;grid-row:2;height:100%}}
@media(max-width:599px){.dispatch-side-panel{width:100%;height:530px}.dispatch-side-panel.is-schedule{height:560px}.dispatch-workspace{grid-template-rows:auto 480px}}
@media(prefers-reduced-motion:reduce){.dispatch-toast-enter-active,.dispatch-toast-leave-active{transition:none}}
.dispatch-confirm-backdrop{position:fixed;z-index:100;inset:0;display:grid;place-items:center;padding:20px;background:#24313c5c;backdrop-filter:blur(5px)}.dispatch-confirm{box-sizing:border-box;width:min(360px,100%);padding:20px;color:var(--text-primary);background:var(--panel-bg-strong);border:1px solid var(--panel-border);border-radius:15px;box-shadow:0 20px 60px #17222e35}.dispatch-confirm h2{margin:0 0 8px;font-size:17px}.dispatch-confirm p{margin:0;color:var(--text-secondary);font-size:12px;line-height:1.6}.dispatch-confirm-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:18px}.dispatch-confirm-actions button{min-width:70px;height:32px;padding:0 12px;color:var(--text-primary);background:var(--search-background);border:1px solid var(--panel-border);border-radius:7px;cursor:pointer}.dispatch-confirm-actions button:focus-visible{outline:2px solid var(--theme-primary);outline-offset:2px}.dispatch-confirm-actions .is-danger{color:#fff;background:#c85c50;border-color:#c85c50}
</style>
