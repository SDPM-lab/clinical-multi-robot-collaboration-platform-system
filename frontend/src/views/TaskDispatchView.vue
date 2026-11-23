<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import TaskScheduleSidebar from '@/components/dispatch/TaskScheduleSidebar.vue'
import TaskForm from '@/components/dispatch/TaskForm.vue'
import DispatchMapScene from '@/components/dispatch/DispatchMapScene.vue'
import { PPO_TASK_WAYPOINT_IDS } from '@/config/dispatchDestinations.js'
import { TASK_LOCATION_IDS } from '@/config/taskTypes.js'
import { t, translateTask } from '@/i18n/index.js'
import { notificationStore } from '@/stores/notificationStore.js'
import { taskApi, toScheduleTask } from '@/services/taskApi.js'

const props = defineProps({ initialPanel: { type: String, default: 'create' } })
const destination = ref('ward_a_2')
const source = ref('pharmacy')
const now = new Date()
const selectedDate = ref(`${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`)
const activePanel = ref(props.initialPanel === 'schedule' ? 'schedule' : 'create')
const panelTopOffset = ref(2)
const activatePanel = async (panel, focus = false) => {
  activePanel.value = panel
  if (focus) { await nextTick(); document.getElementById(`dispatch-${panel}-tab`)?.focus() }
}
const apiTasks = ref([])
const robots = ref([])
const places = ref([])
const selectedTaskType = ref('medication_delivery')
const submitting = ref(false)
const createdTask = ref(null)
const taskForm = ref(null)
watch(() => props.initialPanel, panel => { activePanel.value = panel === 'schedule' ? 'schedule' : 'create' })
let taskRefreshTimer
let refreshingTasks = false
let disposed = false
const loadTasks = async () => {
  const tasks = await taskApi.getTasks()
  if (!disposed) apiTasks.value = tasks
}
const loadPlaces = async () => { places.value = await taskApi.getPlaces() }
const dataLoading = ref(true)
const dataStale = ref(false)
const refreshData = async () => {
  if (refreshingTasks || disposed) return
  refreshingTasks = true
  try {
    const requests = [loadTasks(), taskApi.getRobots()]
    if (!places.value.length) requests.push(loadPlaces())
    const results = await Promise.allSettled(requests)
    if (disposed) return
    if (results[1].status === 'fulfilled') robots.value = results[1].value
    dataStale.value = results.some(result => result.status === 'rejected')
  } finally { refreshingTasks = false; dataLoading.value = false }
}
onMounted(() => {
  refreshData()
  taskRefreshTimer = window.setInterval(refreshData, 5000)
})
onBeforeUnmount(() => { disposed = true; window.clearInterval(taskRefreshTimer) })
const terminalStatuses = new Set(['completed', 'failed', 'cancelled'])
const visibleTasks = computed(() => apiTasks.value.filter(task =>
  task.date === selectedDate.value && !terminalStatuses.has(String(task.status).toLowerCase())))
const selectionStep = ref(0)
const routeConfirmed = ref(false)
const chosenSource = ref(false)
const chosenDestination = ref(false)
const scheduleEditing = ref(false)
watch(activePanel, () => { scheduleEditing.value = false })
const errorMessage = ref('')
const notifyError = message => {
  const known = ['connectionError', 'requestDenied', 'signInRequired', 'apiNotFound', 'serverUnavailable', 'apiError']
  const name = known.find(key => message === t(`dispatch.${key}`))
  notificationStore.add(name ? { key: `dispatch.${name}`, type: 'error' } : { text: message, type: 'error' })
}
const deletedSuccessfully = ref(false)
const pendingDelete = ref(null)
const deletingTaskId = ref(null)
const cancelDeleteButton = ref(null)
const viewportWidth = ref(window.innerWidth)
const syncViewportWidth = () => { viewportWidth.value = window.innerWidth }
onMounted(() => window.addEventListener('resize', syncViewportWidth))
onBeforeUnmount(() => window.removeEventListener('resize', syncViewportWidth))
const mapInsets = computed(() => ({ left: 0, right: 0, top: 0, bottom: viewportWidth.value >= 1100 ? 150 : 0 }))
const placeIds = computed(() => new Set(places.value.map(place => place.id)))
const sourceLocations = computed(() => (TASK_LOCATION_IDS[selectedTaskType.value]?.sources || []).filter(id => placeIds.value.has(id)))
const destinationLocations = computed(() => (TASK_LOCATION_IDS[selectedTaskType.value]?.destinations || []).filter(id => placeIds.value.has(id)))
const fixedSource = computed(() => sourceLocations.value.length === 1)
const fixedDestination = computed(() => destinationLocations.value.length === 1)
const locations = computed(() => fixedSource.value ? destinationLocations.value : fixedDestination.value ? sourceLocations.value : selectionStep.value === 1 ? destinationLocations.value : sourceLocations.value)
watch([selectedTaskType, sourceLocations, destinationLocations], () => {
  chosenSource.value = fixedSource.value && sourceLocations.value.includes(source.value)
  chosenDestination.value = fixedDestination.value && destinationLocations.value.includes(destination.value)
  routeConfirmed.value = chosenSource.value && chosenDestination.value
  selectionStep.value = chosenSource.value && !chosenDestination.value ? 1 : routeConfirmed.value ? 2 : 0
})
const selectMapLocation = (waypointId) => {
  activePanel.value = 'create'
  if (fixedSource.value || (!fixedDestination.value && selectionStep.value === 1)) {
    if (!destinationLocations.value.includes(waypointId)) return
    destination.value = waypointId
    chosenDestination.value = true
    selectionStep.value = 2
    routeConfirmed.value = true
  } else {
    if (!sourceLocations.value.includes(waypointId)) return
    source.value = waypointId
    chosenSource.value = true
    chosenDestination.value = fixedDestination.value && destinationLocations.value.includes(destination.value)
    selectionStep.value = chosenDestination.value ? 2 : 1
    routeConfirmed.value = chosenDestination.value
  }
}
const selectFormLocation = (field, waypointId) => {
  if (field === 'source') { source.value = waypointId; chosenSource.value = true }
  else { destination.value = waypointId; chosenDestination.value = true }
  if (fixedSource.value && sourceLocations.value.includes(source.value)) chosenSource.value = true
  if (fixedDestination.value && destinationLocations.value.includes(destination.value)) chosenDestination.value = true
  routeConfirmed.value = chosenSource.value && chosenDestination.value
  selectionStep.value = routeConfirmed.value ? 2 : chosenSource.value ? 1 : 0
}
const pendingReschedule = ref(null)
const rescheduling = ref(false)
const rescheduleError = ref('')
const cancelRescheduleButton = ref(null)
watch(pendingReschedule, async value => { if (value) { await nextTick(); cancelRescheduleButton.value?.focus() } })
const handleSaveTaskEdits = (taskId, time) => {
  const task = apiTasks.value.find(item => item.id === taskId)
  if (!task || !['pending', 'assigned'].includes(String(task.status).toLowerCase()) || task.startedAt) return
  if (time === task.startTime.slice(0, 5)) return
  rescheduleError.value = ''
  pendingReschedule.value = { task, time }
}
const savingTaskIds = new Set()
const confirmReschedule = async () => {
  if (!pendingReschedule.value || rescheduling.value) return
  const { task: selectedTask, time } = pendingReschedule.value
  const taskId = selectedTask.id
  const task = apiTasks.value.find(task => task.id === taskId)
  if (!task || !['pending', 'assigned'].includes(String(task.status).toLowerCase()) || task.startedAt || savingTaskIds.has(taskId)) { pendingReschedule.value = null; return }
  if (time === task.startTime.slice(0, 5)) return
  savingTaskIds.add(taskId)
  rescheduling.value = true
  rescheduleError.value = ''
  deletedSuccessfully.value = false
  createdTask.value = null
  try {
    const replacement = await taskApi.updateSchedule(taskId, new Date(`${task.date}T${time}:00`).toISOString())
    // Apply the authoritative replacement immediately, even if the next list refresh fails.
    apiTasks.value = apiTasks.value.filter(item => item.id !== taskId)
    apiTasks.value.push(toScheduleTask(replacement))
    pendingReschedule.value = null
    errorMessage.value = t('dispatch.taskChangesSaved')
    notificationStore.add({ key: 'dispatch.taskChangesSaved', type: 'success' })
    try { await loadTasks() } catch { dataStale.value = true }
  } catch (error) { rescheduleError.value = error.message || t('dispatch.apiError'); errorMessage.value = rescheduleError.value; notifyError(errorMessage.value) }
  finally { savingTaskIds.delete(taskId); rescheduling.value = false }
}
watch(pendingDelete, async (task) => { if (task) { await nextTick(); cancelDeleteButton.value?.focus() } })
const confirmDelete = async () => {
  if (!pendingDelete.value || deletingTaskId.value) return
  const taskToDelete = pendingDelete.value
  deletingTaskId.value = taskToDelete.id
  createdTask.value = null
  try {
    const code = taskToDelete.taskCode || taskToDelete.id
    await taskApi.deleteTask(taskToDelete.id)
    apiTasks.value = apiTasks.value.filter(task => task.id !== taskToDelete.id)
    deletedSuccessfully.value = true
    errorMessage.value = t('dispatch.deleted', { id: code })
    notificationStore.add({ key: 'dispatch.deleted', params: { id: code }, type: 'success' })
    pendingDelete.value = null
    try { await loadTasks(); dataStale.value = false } catch { dataStale.value = true }
  } catch (error) { deletedSuccessfully.value = false; errorMessage.value = error.message || t('dispatch.apiError'); notifyError(errorMessage.value) }
  finally { deletingTaskId.value = null }
}
const handleCreateTask = async (payload) => {
  if (submitting.value) return
  submitting.value = true
  deletedSuccessfully.value = false
  createdTask.value = null
  errorMessage.value = ''
  try {
    const task = await taskApi.createTask(payload)
    createdTask.value = { id: task.taskCode || task.id, title: payload.type }
    notificationStore.add({ key: 'dispatch.created', params: { id: task.taskCode || task.id }, taskTitle: payload.type, type: 'success' })
    selectedDate.value = payload.date
    await nextTick()
    taskForm.value?.reset()
    await nextTick()
    chosenSource.value = sourceLocations.value.length === 1
    chosenDestination.value = destinationLocations.value.length === 1
    routeConfirmed.value = chosenSource.value && chosenDestination.value
    selectionStep.value = chosenSource.value && !chosenDestination.value ? 1 : 0
  } catch (error) { errorMessage.value = error.message || t('dispatch.apiError'); notifyError(errorMessage.value) }
  finally { submitting.value = false }
  if (createdTask.value) {
    try { await loadTasks() } catch { errorMessage.value = t('dispatch.apiLoadError'); notificationStore.add({ key: 'dispatch.apiLoadError', type: 'error' }) }
  }
}
const dismissNotification = () => { errorMessage.value = ''; createdTask.value = null }
const isWarning = computed(() => !!errorMessage.value && !deletedSuccessfully.value && ![t('dispatch.saved'), t('dispatch.prioritySaved'), t('dispatch.taskChangesSaved')].includes(errorMessage.value))
const isCreateSuccess = computed(() => !errorMessage.value && !!createdTask.value)
const notification = computed(() => errorMessage.value || (createdTask.value
  ? t('dispatch.created', { id: createdTask.value.id, title: translateTask(createdTask.value.title) }) : ''))
let notificationTimer
watch([notification, isWarning], ([message, warning]) => {
  window.clearTimeout(notificationTimer)
  if (message && !warning) notificationTimer = window.setTimeout(dismissNotification, 5000)
})
onBeforeUnmount(() => window.clearTimeout(notificationTimer))

</script>

<template>
  <div class="task-dispatch-page">
    <div class="dispatch-data-status" :class="{ 'is-stale': dataStale }" role="status">
      <span>{{ t(dataLoading ? 'dispatchUx.loading' : dataStale ? 'dispatchUx.stale' : 'dispatchUx.live') }}</span>
      <button v-if="dataStale" type="button" @click="refreshData">{{ t('dispatchUx.retry') }}</button>
    </div>
    <div class="dispatch-workspace">
      <aside class="dispatch-side-panel" :style="{ '--panel-top-offset': `${panelTopOffset}px` }">
        <div class="dispatch-panel-tabs" role="tablist" :aria-label="t('dispatch.panelTabs')" @keydown.left.prevent="activatePanel('create', true)" @keydown.right.prevent="activatePanel('schedule', true)">
          <button id="dispatch-create-tab" type="button" role="tab" :aria-selected="activePanel === 'create'" aria-controls="dispatch-create-panel" :tabindex="activePanel === 'create' ? 0 : -1" @click="activatePanel('create')">{{ t('dispatchForm.title') }}</button>
          <button id="dispatch-schedule-tab" type="button" role="tab" :aria-selected="activePanel === 'schedule'" aria-controls="dispatch-schedule-panel" :tabindex="activePanel === 'schedule' ? 0 : -1" @click="activatePanel('schedule')">{{ t('dispatch.scheduleTab') }}</button>
        </div>
        <div v-show="activePanel === 'create'" id="dispatch-create-panel" class="dispatch-panel-body" role="tabpanel" aria-labelledby="dispatch-create-tab">
          <TaskForm ref="taskForm" :submitting="submitting" :destination="destination" :source="source" :date="selectedDate" :locations="PPO_TASK_WAYPOINT_IDS.filter(id => placeIds.has(id))" @update:task-type="selectedTaskType = $event" @update:source="selectFormLocation('source', $event)" @update:destination="selectFormLocation('destination', $event)" @submit="handleCreateTask" />
        </div>
        <div v-show="activePanel === 'schedule'" id="dispatch-schedule-panel" class="dispatch-panel-body" role="tabpanel" aria-labelledby="dispatch-schedule-tab">
          <TaskScheduleSidebar v-model:date="selectedDate" :editing="scheduleEditing" :robots="robots" :tasks="visibleTasks" @edit="scheduleEditing = !scheduleEditing" @save-edits="handleSaveTaskEdits" @request-delete="pendingDelete = $event" />
        </div>
      </aside>
      <p class="dispatch-map-help">{{ t(selectionStep === 1 ? 'dispatchUx.mapDestination' : selectionStep === 2 ? 'dispatchUx.mapReady' : 'dispatchUx.mapSource') }}</p>
      <DispatchMapScene class="dispatch-map" :robots="robots" :source="source" :destination="destination" :selection-step="selectionStep" :route-confirmed="routeConfirmed" :show-source-pin="chosenSource" :show-destination-pin="chosenDestination" :allowed-locations="locations" :viewport-insets="mapInsets" @select-location="selectMapLocation" @visual-top-change="panelTopOffset = Math.max(0, $event - 8)" />
    </div>
    <div v-if="pendingReschedule" class="dispatch-confirm-backdrop" @click.self="!rescheduling && (pendingReschedule=null)" @keydown.esc="!rescheduling && (pendingReschedule=null)">
      <section class="dispatch-confirm" role="alertdialog" aria-modal="true" aria-labelledby="dispatch-reschedule-title" aria-describedby="dispatch-reschedule-message" :aria-busy="rescheduling">
        <h2 id="dispatch-reschedule-title">{{ t('dispatchUx.rescheduleTitle') }}</h2>
        <p id="dispatch-reschedule-message">{{ t('dispatchUx.rescheduleMessage', { id: pendingReschedule.task.taskCode || pendingReschedule.task.id, time: pendingReschedule.time }) }}</p>
        <p v-if="rescheduleError" class="reschedule-error" role="alert">{{ rescheduleError }}</p>
        <div class="dispatch-confirm-actions"><button ref="cancelRescheduleButton" type="button" :disabled="rescheduling" @click="pendingReschedule=null">{{ t('dispatch.cancel') }}</button><button class="confirm-reschedule" type="button" :disabled="rescheduling" @click="confirmReschedule">{{ t(rescheduling ? 'dispatchUx.creating' : 'dispatchUx.requeue') }}</button></div>
      </section>
    </div>
    <div v-if="pendingDelete" class="dispatch-confirm-backdrop" @click.self="!deletingTaskId && (pendingDelete=null)" @keydown.esc="!deletingTaskId && (pendingDelete=null)">
      <section class="dispatch-confirm" role="alertdialog" aria-modal="true" aria-labelledby="dispatch-delete-title" aria-describedby="dispatch-delete-message" :aria-busy="Boolean(deletingTaskId)">
        <h2 id="dispatch-delete-title">{{ t('dispatch.deleteTitle') }}</h2>
        <p id="dispatch-delete-message">{{ t('dispatch.deleteMessage', { id: pendingDelete.taskCode || pendingDelete.id, title: translateTask(pendingDelete.title) }) }}</p>
        <div class="dispatch-confirm-actions"><button ref="cancelDeleteButton" type="button" :disabled="Boolean(deletingTaskId)" @click="pendingDelete=null">{{ t('dispatch.cancel') }}</button><button type="button" class="is-danger" :disabled="Boolean(deletingTaskId)" @click="confirmDelete">{{ t(deletingTaskId ? 'dispatchUx.deleting' : 'dispatch.delete') }}</button></div>
      </section>
    </div>
    <Transition name="dispatch-toast"><div v-if="notification" class="dispatch-toast" :class="{ 'is-schedule-update': [t('dispatch.saved'), t('dispatch.prioritySaved'), t('dispatch.taskChangesSaved')].includes(errorMessage), 'is-create-success': isCreateSuccess, 'is-delete-success': deletedSuccessfully && !!errorMessage, 'is-warning': isWarning }" :role="isWarning ? 'alert' : 'status'">{{ notification }}<button type="button" :aria-label="t('dispatch.closeNotification')" @click="dismissNotification">×</button></div></Transition>
  </div>
</template>

<style scoped>
.task-dispatch-page{--dispatch-accent:#FB9966;position:absolute;inset:0;box-sizing:border-box;width:100%;height:100dvh;padding-top:64px;overflow:hidden;color:var(--text-primary)}
.dispatch-workspace{display:grid;grid-template-columns:clamp(360px,26vw,420px) minmax(0,1fr);gap:14px;position:relative;box-sizing:border-box;width:100%;height:100%;min-height:0;padding:6px 24px 12px;container-type:inline-size}.dispatch-map{grid-column:2;grid-row:1;position:relative;min-width:0;min-height:0}.dispatch-side-panel{z-index:10;grid-column:1;grid-row:1;display:grid;grid-template-rows:45px minmax(0,1fr);align-self:start;box-sizing:border-box;width:100%;--panel-offset:max(0px,calc(var(--panel-top-offset,0px) - 32px));height:min(620px,calc(100dvh - var(--panel-offset) - 96px));margin-top:var(--panel-offset);container-type:inline-size;min-height:0;overflow:hidden;color:var(--text-primary);background:var(--surface-glass);border:1px solid var(--glass-border);border-radius:16px;box-shadow:0 18px 52px #34433820;backdrop-filter:blur(24px) saturate(115%);-webkit-backdrop-filter:blur(24px) saturate(115%)}.dispatch-panel-tabs{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:5px;padding:7px 9px 0;border-bottom:1px solid color-mix(in srgb,var(--dispatch-tertiary-accent) 28%,var(--glass-divider))}.dispatch-panel-tabs button{min-width:0;padding:0 8px;color:var(--text-secondary);background:transparent;border:0;border-bottom:2px solid transparent;border-radius:8px 8px 0 0;font:inherit;font-size:15px;font-weight:550;cursor:pointer}.dispatch-panel-tabs button:hover{background:color-mix(in srgb,var(--theme-primary) 8%,transparent)}.dispatch-panel-tabs button[aria-selected=true]{color:var(--text-primary);background:color-mix(in srgb,var(--theme-primary) 10%,transparent);border-bottom-color:var(--theme-primary);font-weight:650}.dispatch-panel-tabs button:focus-visible{outline:2px solid var(--theme-primary);outline-offset:-2px}.dispatch-panel-body{min-width:0;min-height:0}.dispatch-panel-body :deep(.task-panel){background:transparent;border:0;border-radius:0;box-shadow:none;backdrop-filter:none;-webkit-backdrop-filter:none}.dispatch-panel-body :deep(.task-panel > header){display:none}.dispatch-panel-body :deep(.schedule-header h2){display:none}.dispatch-panel-body :deep(.schedule-header){justify-content:flex-end;padding-top:8px;padding-bottom:5px}.dispatch-panel-body :deep(.schedule-list){padding-bottom:14px}
:global([data-theme='dark'] .dispatch-side-panel){background:rgba(48,41,37,.96);border-color:rgba(255,243,236,.10);box-shadow:0 18px 52px rgba(0,0,0,.24);backdrop-filter:blur(20px) saturate(110%);-webkit-backdrop-filter:blur(20px) saturate(110%)}
.dispatch-toast{position:fixed;z-index:80;right:28px;top:78px;max-width:360px;padding:12px 16px;color:var(--text-primary);font-size:13px;background:var(--panel-bg-strong);border:1px solid var(--panel-border);border-radius:8px;box-shadow:var(--dropdown-shadow)}.dispatch-toast button{margin-left:12px;border:0;background:none;color:inherit;cursor:pointer}.dispatch-toast-enter-active,.dispatch-toast-leave-active{transition:opacity .2s}.dispatch-toast-enter-from,.dispatch-toast-leave-to{opacity:0}
@media(max-width:1099px){.task-dispatch-page{inset:64px 0 0;height:auto;padding-top:0;overflow-y:auto}.dispatch-workspace{grid-template-columns:minmax(0,1fr);grid-template-rows:auto minmax(520px,65vh);height:auto;min-height:100%;padding:8px 12px 12px;gap:12px}.dispatch-side-panel{grid-column:1;grid-row:1;width:min(100%,520px);min-height:min(360px,max(0px,calc(100dvh - var(--panel-offset) - 96px)));margin-top:0}.dispatch-map{grid-column:1;grid-row:2;height:100%}}
@media(max-width:599px){.dispatch-side-panel{width:100%}.dispatch-workspace{grid-template-rows:auto 480px}}
@media(prefers-reduced-motion:reduce){.dispatch-toast-enter-active,.dispatch-toast-leave-active{transition:none}}
.dispatch-confirm-backdrop{position:fixed;z-index:100;inset:0;display:grid;place-items:center;padding:20px;background:#24313c5c;backdrop-filter:blur(5px)}.dispatch-confirm{box-sizing:border-box;width:min(360px,100%);padding:20px;color:var(--text-primary);background:var(--panel-bg-strong);border:1px solid var(--panel-border);border-radius:15px;box-shadow:0 20px 60px #17222e35}.dispatch-confirm h2{margin:0 0 8px;font-size:17px}.dispatch-confirm p{margin:0;color:var(--text-secondary);font-size:12px;line-height:1.6}.dispatch-confirm-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:18px}.dispatch-confirm-actions button{min-width:70px;height:32px;padding:0 12px;color:var(--text-primary);background:var(--search-background);border:1px solid var(--panel-border);border-radius:7px;cursor:pointer}.dispatch-confirm-actions button:focus-visible{outline:2px solid var(--theme-primary);outline-offset:2px}.dispatch-confirm-actions .is-danger{color:#fff;background:#c85c50;border-color:#c85c50}
.task-dispatch-page{overflow-y:auto}
#dispatch-create-panel :deep(.task-form-grid){row-gap:11px}
#dispatch-create-panel :deep(.notes-field textarea){min-height:100px}
</style>

<style scoped>
.dispatch-toast.is-schedule-update{color:#265d40;background:#eaf7ee;border:1px solid #b5d9c1;box-shadow:0 8px 28px #366c4820}
</style>

<style scoped>
.dispatch-toast.is-create-success{color:#265d40;background:#eaf7ee;border:1px solid #b5d9c1;box-shadow:0 8px 28px #366c4820}
.dispatch-confirm{width:min(480px,100%);padding:28px;border-radius:18px}
.dispatch-confirm h2{font-size:21px;margin-bottom:12px}.dispatch-confirm p{font-size:14px;line-height:1.7}
.dispatch-confirm-actions{margin-top:26px;gap:12px}.dispatch-confirm-actions button{min-width:96px;height:42px;font-size:14px;border:0;transition:background .15s,color .15s}
.dispatch-confirm-actions button:hover{color:#783c20;background:#ffe4d4;box-shadow:none}
.dispatch-confirm .reschedule-error{color:#9b2836;padding:8px;border-radius:6px;background:#fff0f0}
.dispatch-confirm-actions button:disabled{opacity:.55;cursor:wait}
.dispatch-confirm-actions .is-danger:hover{background:#ab4238;box-shadow:none}
@media(prefers-reduced-motion:reduce){.dispatch-confirm-actions button{transition:none}}
</style>

<style scoped>
.dispatch-toast.is-delete-success{color:#285c80;background:#eaf4ff;border:1px solid #bad7ef;box-shadow:0 8px 28px #386f9620}
</style>

<style scoped>
.dispatch-toast.is-warning{color:#873d43;background:#fff0f0;border:1px solid #efb9bf;box-shadow:0 8px 28px #ab4b5520}
</style>

<style scoped>
.task-dispatch-page{--dispatch-hint-bg:var(--dispatch-hint-surface);--dispatch-hint-border:var(--dispatch-hint-outline);--dispatch-hint-text:var(--dispatch-hint-foreground)}
.dispatch-workspace{height:calc(100% - 42px)}
.dispatch-data-status{display:flex;align-items:center;gap:10px;padding:6px 20px;color:var(--text-secondary);font-size:12px;line-height:1.5;min-height:30px;box-sizing:border-box}
.dispatch-data-status.is-stale{color:#922f3c;background:#fff0f0}.dispatch-data-status button{padding:3px 10px;border:1px solid currentColor;border-radius:5px;color:inherit;background:transparent;cursor:pointer}
.dispatch-map-help{position:absolute;z-index:2;bottom:12px;right:20px;max-width:min(540px,calc(100% - 40px));margin:0;padding:10px 14px;border:1px solid var(--dispatch-hint-border);border-radius:10px;background:var(--dispatch-hint-bg);color:var(--dispatch-hint-text);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);font-size:12px;line-height:1.6;pointer-events:none}
@media(max-width:1099px){.dispatch-workspace{height:auto}.dispatch-map-help{position:relative;bottom:auto;right:auto;grid-column:1;grid-row:3;max-width:none;margin:8px 12px}}
:global([data-theme='dark']) .dispatch-data-status.is-stale{color:#ffd3d8;background:#512b33}
#dispatch-create-panel{min-height:0;max-height:none;overflow:hidden;overscroll-behavior:contain}
#dispatch-create-panel :deep(.task-panel){height:100%;grid-template-rows:auto minmax(0,1fr)}
#dispatch-create-panel :deep(.task-panel form){min-height:0;grid-template-rows:minmax(0,1fr) auto}
#dispatch-create-panel :deep(.form-scroll){min-height:0;overflow-y:hidden;overscroll-behavior:none;padding-block:3px}
#dispatch-create-panel :deep(.task-form-grid){align-items:start;column-gap:10px;row-gap:18px}
#dispatch-create-panel :deep(.task-form-grid .field>span:first-child),#dispatch-create-panel :deep(.task-form-grid .field>label),#dispatch-create-panel :deep(.priority-control legend){min-height:18px;line-height:18px}
#dispatch-create-panel :deep(.task-type-trigger),#dispatch-create-panel :deep(.location-trigger),#dispatch-create-panel :deep(.date-trigger),#dispatch-create-panel :deep(.dispatch-time-entry){height:32px}
#dispatch-create-panel :deep(.task-type-trigger),#dispatch-create-panel :deep(.location-trigger),#dispatch-create-panel :deep(.date-trigger),#dispatch-create-panel :deep(.dispatch-time-entry input){font-size:12px}
#dispatch-create-panel :deep(.priority-control button){height:28px}
#dispatch-create-panel :deep(.notes-field textarea){min-height:clamp(84px,11vh,104px);height:clamp(84px,11vh,104px);line-height:1.55;resize:none}
@container (max-width:430px){#dispatch-create-panel :deep(.task-form-grid){grid-template-columns:minmax(0,1fr)}}
@media(max-width:599px) and (max-height:660px){.dispatch-workspace{padding-top:2px}}
@media(max-height:660px){#dispatch-create-panel :deep(.task-form-grid){row-gap:7px}#dispatch-create-panel :deep(.form-scroll){padding-block:0}}
.task-dispatch-page .dispatch-panel-tabs button[aria-selected=true]{background:color-mix(in srgb,var(--theme-primary) 10%,transparent)}
.task-dispatch-page .dispatch-map-help{border-color:var(--dispatch-hint-outline);background:var(--dispatch-hint-surface);color:var(--dispatch-hint-foreground)}
@media (max-width:1099px) and (orientation:landscape){
  .task-dispatch-page{inset:64px 0 0;height:auto;padding-top:0;overflow:hidden}
  .dispatch-workspace{grid-template-columns:minmax(300px,34%) minmax(0,1fr);grid-template-rows:minmax(0,1fr);height:calc(100% - 30px);min-height:0;padding:4px 12px 12px}
  .dispatch-side-panel{grid-column:1;grid-row:1;width:100%;height:min(540px,100%);min-height:0;margin:0}
  .dispatch-map{grid-column:2;grid-row:1;height:100%}
  .dispatch-map-help{position:absolute;grid-column:auto;grid-row:auto;right:20px;bottom:12px;max-width:min(440px,calc(66% - 40px));margin:0}
  #dispatch-create-panel :deep(.task-form-grid){grid-template-columns:repeat(2,minmax(0,1fr));row-gap:8px}
  #dispatch-create-panel :deep(.form-scroll){overflow-y:auto;overscroll-behavior:contain}
  #dispatch-create-panel :deep(.notes-field textarea){min-height:60px;height:60px}
}
</style>
