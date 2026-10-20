<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { ChevronDown, Clock3 } from '@lucide/vue'
import { t, translateLocation, translateTask } from '@/i18n/index.js'
import { robotStateLabels } from '@/data/robotStatus.js'
import { getRobotVisualTheme } from '@/config/robotVisualThemes.js'
import { taskPriorityColor } from '@/config/taskPriorityColors.js'
import { REQUIRED_CAPABILITIES_BY_TASK_TYPE, TASK_TYPE_BY_LABEL, TASK_TYPE_LABELS } from '@/config/taskTypes.js'

const props = defineProps({
  robots: { type: Array, required: true },
  locations: { type: Array, required: true },
  destination: { type: String, default: '' },
  origin: { type: String, default: 'Pharmacy' },
  robotId: { type: String, default: 'R01' },
  date: { type: String, required: true },
})
const emit = defineEmits(['submit', 'update:destination', 'update:origin', 'update:robotId'])
const taskTypes = TASK_TYPE_LABELS
const priorities = [{ value: 'low' }, { value: 'normal' }, { value: 'high' }, { value: 'emergency' }]
const DEFAULT_DURATION_SECONDS = 12 * 60
const taskTypeOpen = ref(false)
const taskTypePicker = ref(null)
const originPickerOpen = ref(false)
const destinationPickerOpen = ref(false)
const originPicker = ref(null)
const destinationPicker = ref(null)
const robotPickerOpen = ref(false)
const robotPicker = ref(null)
const timePickerOpen = ref(false)
const timePicker = ref(null)
const timeText = ref('09:30 AM')
const timeOptions = Array.from({ length: 48 }, (_, index) => { const hour = Math.floor(index / 2); return `${String(hour % 12 || 12).padStart(2, '0')}:${index % 2 ? '30' : '00'} ${hour < 12 ? 'AM' : 'PM'}` })
const parseTimeText = (value) => {
  const match = /^(0?[1-9]|1[0-2]):([0-5][0-9])\s*(AM|PM)$/i.exec(value.trim())
  if (!match) return null
  const hour = Number(match[1]) % 12 + (match[3].toUpperCase() === 'PM' ? 12 : 0)
  return `${String(hour).padStart(2, '0')}:${match[2]}:00`
}
const normalizeTimeText = () => { const time = parseTimeText(timeText.value); if (time) { const hour = Number(time.slice(0, 2)); timeText.value = `${String(hour % 12 || 12).padStart(2, '0')}:${time.slice(3, 5)} ${hour < 12 ? 'AM' : 'PM'}` } }
const chooseTime = (value) => { timeText.value = value; timePickerOpen.value = false }
const robotStateKey = { busy: 'robotStateBusy', idle: 'robotStateIdle', charging: 'robotStateCharging', error: 'robotStateError', offline: 'robotStateOffline' }
const robotStateText = (robot) => robotStateKey[robot.state] ? t(`dispatch.${robotStateKey[robot.state]}`) : robotStateLabels[robot.state] || robot.state
const selectRobot = (id) => { form.robotId = id; robotPickerOpen.value = false }
const selectLocation = (field, value) => {
  if (field === 'origin') { originValue.value = value; originPickerOpen.value = false }
  else { destinationValue.value = value; destinationPickerOpen.value = false }
}
const onOutsidePointer = (event) => {
  if (!taskTypePicker.value?.contains(event.target)) taskTypeOpen.value = false
  if (!robotPicker.value?.contains(event.target)) robotPickerOpen.value = false
  if (!timePicker.value?.contains(event.target)) timePickerOpen.value = false
  if (!originPicker.value?.contains(event.target)) originPickerOpen.value = false
  if (!destinationPicker.value?.contains(event.target)) destinationPickerOpen.value = false
}
onMounted(() => document.addEventListener('pointerdown', onOutsidePointer))
onBeforeUnmount(() => document.removeEventListener('pointerdown', onOutsidePointer))

const makeDefaults = () => ({
  type: '藥品配送', robotId: props.robotId || 'R01',
  date: props.date,
  priority: 'normal', note: '',
})
const form = reactive(makeDefaults())
const originValue = computed({ get: () => props.origin, set: (value) => emit('update:origin', value) })
const destinationValue = computed({ get: () => props.destination, set: (value) => emit('update:destination', value) })
const selectedRobot = computed(() => props.robots.find((robot) => robot.id === form.robotId))
const requiredCapabilities = computed(() => REQUIRED_CAPABILITIES_BY_TASK_TYPE[TASK_TYPE_BY_LABEL[form.type]] || [])

watch(() => props.robotId, (value) => { if (value && value !== form.robotId) form.robotId = value })
watch(() => props.date, (value) => { form.date = value })
watch(() => form.robotId, (value) => emit('update:robotId', value), { immediate: true })
watch(timePickerOpen, async (open) => {
  if (!open) return
  await nextTick()
  const index = timeOptions.indexOf(timeText.value)
  const list = timePicker.value?.querySelector('.dispatch-time-options')
  if (list && index >= 0) list.scrollTop = Math.max(0, index * 29 - list.clientHeight / 2)
})

const reset = () => {
  Object.assign(form, makeDefaults())
  timeText.value = '09:30 AM'
  taskTypeOpen.value = false
  timePickerOpen.value = false
}
const submit = () => {
  const startTime = parseTimeText(timeText.value)
  if (!startTime) return
  emit('submit', {
    robotId: form.robotId, title: form.type, type: form.type,
    taskType: TASK_TYPE_BY_LABEL[form.type],
    origin: originValue.value, destination: destinationValue.value, date: form.date,
    startTime, durationSeconds: DEFAULT_DURATION_SECONDS,
    priority: form.priority, note: form.note,
  })
}
</script>

<template>
  <section class="task-panel" :class="{ 'is-robot-picker-open': robotPickerOpen }" :aria-label="t('dispatchForm.title')">
    <header><div><span class="panel-eyebrow">{{ t('dispatchForm.eyebrow') }}</span><strong>{{ t('dispatchForm.title') }}</strong></div></header>
    <form @submit.prevent="submit">
      <div class="form-scroll task-form-grid">
        <div ref="taskTypePicker" class="field task-type-picker full-width" @keydown.esc.stop="taskTypeOpen=false"><span>{{ t('dispatchForm.type') }}</span><button type="button" class="task-type-trigger" :aria-label="t('dispatchForm.type')" :aria-expanded="taskTypeOpen" aria-haspopup="listbox" @click="taskTypeOpen=!taskTypeOpen"><span>{{ translateTask(form.type) }}</span><ChevronDown :size="14" /></button><div v-if="taskTypeOpen" class="task-type-options" role="listbox" :aria-label="t('dispatchForm.type')"><button v-for="type in taskTypes" :key="type" type="button" role="option" :aria-selected="form.type===type" @click="form.type=type;taskTypeOpen=false">{{ translateTask(type) }}</button></div></div>
        <div class="required-capabilities full-width"><span>{{ t('dispatchForm.requiredCapabilities') }}</span><div><span v-for="capability in requiredCapabilities" :key="capability" :data-capability="capability">{{ t(`dispatchForm.capabilities.${capability}`) }}</span></div></div>

        <div ref="robotPicker" class="field full-width dispatch-robot-picker" @keydown.esc.stop="robotPickerOpen=false">
          <span>{{ t('dispatch.robotSelect') }}</span>
          <button type="button" class="robot-trigger" :aria-label="t('dispatch.robotSelect')" :aria-expanded="robotPickerOpen" aria-haspopup="listbox" @click="robotPickerOpen=!robotPickerOpen">
            <span class="robot-trigger-name">{{ selectedRobot?.name || form.robotId }}</span><span class="robot-trigger-state">{{ selectedRobot ? robotStateText(selectedRobot) : '' }}</span><span class="robot-trigger-battery">{{ selectedRobot?.battery }}%</span><ChevronDown :size="14" />
          </button>
          <div v-if="robotPickerOpen" class="robot-options" role="listbox" :aria-label="t('dispatch.robotSelect')">
            <button v-for="robot in robots" :key="robot.id" type="button" role="option" :aria-selected="form.robotId===robot.id" @click="selectRobot(robot.id)"><i :style="{ backgroundColor: getRobotVisualTheme(robot.id).main }"></i><span class="robot-option-name">{{ robot.name }}</span><span class="robot-option-state">{{ robotStateText(robot) }}</span><strong>{{ robot.battery }}%</strong></button>
          </div>
        </div>
        <div ref="originPicker" class="field dispatch-location-picker" @keydown.esc.stop="originPickerOpen=false"><span>{{ t('dispatchForm.origin') }}</span><button type="button" class="location-trigger" :aria-label="t('dispatchForm.origin')" :aria-expanded="originPickerOpen" aria-haspopup="listbox" @click="originPickerOpen=!originPickerOpen;destinationPickerOpen=false"><span>{{ translateLocation(originValue) }}</span><ChevronDown :size="15" /></button><div v-if="originPickerOpen" class="location-options" role="listbox" :aria-label="t('dispatchForm.origin')"><button v-for="location in locations" :key="location" type="button" role="option" :aria-selected="originValue===location" @click="selectLocation('origin', location)">{{ translateLocation(location) }}</button></div></div>
        <div ref="destinationPicker" class="field dispatch-location-picker" @keydown.esc.stop="destinationPickerOpen=false"><span>{{ t('dispatchForm.destination') }}</span><button type="button" class="location-trigger" :aria-label="t('dispatchForm.destination')" :aria-expanded="destinationPickerOpen" aria-haspopup="listbox" @click="destinationPickerOpen=!destinationPickerOpen;originPickerOpen=false"><span>{{ translateLocation(destinationValue) }}</span><ChevronDown :size="15" /></button><div v-if="destinationPickerOpen" class="location-options" role="listbox" :aria-label="t('dispatchForm.destination')"><button v-for="location in locations" :key="location" type="button" role="option" :aria-selected="destinationValue===location" @click="selectLocation('destination', location)">{{ translateLocation(location) }}</button></div></div>

        <label class="field"><span>{{ t('dispatchForm.date') }}</span><input v-model="form.date" type="date" required></label>
        <div ref="timePicker" class="field dispatch-time-picker" @keydown.esc.stop="timePickerOpen=false"><label for="dispatch-start-time">{{ t('dispatchForm.start') }}</label><div class="dispatch-time-entry"><input id="dispatch-start-time" v-model.trim="timeText" type="text" inputmode="text" pattern="(0?[1-9]|1[0-2]):[0-5][0-9] (AM|PM)" placeholder="09:30 AM" required @blur="normalizeTimeText"><button type="button" :aria-label="t('dispatchForm.chooseTime')" :aria-expanded="timePickerOpen" @click="timePickerOpen=!timePickerOpen"><Clock3 :size="14" /></button></div><div v-if="timePickerOpen" class="dispatch-time-options" role="listbox" :aria-label="t('dispatchForm.chooseTime')"><button v-for="time in timeOptions" :key="time" type="button" role="option" :aria-selected="timeText===time" @click="chooseTime(time)">{{ time }}</button></div></div>

        <fieldset class="priority-control full-width"><legend>{{ t('dispatchForm.priority') }}</legend><div><button v-for="priority in priorities" :key="priority.value" type="button" :data-priority="priority.value" :style="{ '--priority-color': taskPriorityColor(priority.value) }" :class="{ active: form.priority === priority.value }" :aria-pressed="form.priority === priority.value" @click="form.priority=priority.value">{{ t(`priority.${priority.value}`) }}</button></div></fieldset>
        <label class="field notes-field"><span>{{ t('dispatchForm.note') }}</span><textarea v-model.trim="form.note" rows="3" :placeholder="t('dispatchForm.notePlaceholder')"></textarea></label>
      </div>
      <footer><button type="button" @click="reset">{{ t('dispatchForm.cancel') }}</button><button type="submit" class="create-button">{{ t('dispatchForm.create') }}</button></footer>
    </form>
  </section>
</template>

<style scoped>
.task-panel{box-sizing:border-box;display:grid;grid-template-rows:auto minmax(0,1fr);width:100%;max-width:none;height:100%;min-height:0;padding:12px 16px 0;color:var(--text-primary);background:rgba(246,244,239,.78);border:1px solid rgba(255,255,255,.58);border-radius:12px;box-shadow:0 18px 45px rgba(66,59,48,.10);backdrop-filter:blur(22px) saturate(115%);-webkit-backdrop-filter:blur(22px) saturate(115%)}:global([data-theme='dark']) .task-panel{background:rgba(61,65,62,.88);border-color:rgba(255,255,255,.12)}
header{display:flex;align-items:center;justify-content:space-between;padding-bottom:7px;border-bottom:1px solid var(--glass-divider)}header strong{font-size:15px}header button{width:27px;height:27px;color:var(--text-muted);font-size:19px;background:transparent;border:0;border-radius:6px;cursor:pointer}header button:hover{background:var(--icon-button-hover)}form{display:grid;grid-template-rows:minmax(0,1fr) auto;min-height:0}.form-scroll{min-height:0;padding:8px 2px;overflow-y:auto;scrollbar-width:none}.form-scroll::-webkit-scrollbar{display:none}.task-form-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));align-content:start;gap:6px 14px}.field{display:grid;gap:4px;min-width:0;color:var(--text-secondary);font-size:11.5px}.field input,.field select,.field textarea{box-sizing:border-box;width:100%;min-width:0;height:32px;padding:5px 9px;color:var(--text-primary);background:color-mix(in srgb,var(--search-background) 80%,transparent);border:1px solid var(--icon-button-border);border-radius:7px;font:inherit;outline:0}.field textarea{height:auto;min-height:56px;resize:vertical}.field input:focus,.field select:focus,.field textarea:focus{border-color:var(--search-border-active);box-shadow:0 0 0 3px var(--search-focus-ring)}
.computed-time{display:grid;gap:4px;color:var(--text-secondary);font-size:11.5px}.computed-time strong{display:flex;align-items:center;height:32px;color:var(--text-primary);font-size:13px;font-variant-numeric:tabular-nums}
.priority-control{margin:0;padding:0;border:0}.priority-control legend{margin-bottom:5px;color:var(--text-secondary);font-size:11.5px}.priority-control>div{display:grid;grid-template-columns:repeat(4,1fr);padding:2px;background:color-mix(in srgb,var(--progress-track) 74%,transparent);border-radius:7px}.priority-control button{height:29px;color:var(--text-secondary);font-size:11px;background:transparent;border:0;border-radius:5px;cursor:pointer}.priority-control button.active{color:var(--text-primary);background:var(--panel-bg-strong);box-shadow:0 2px 7px rgba(65,58,48,.09)}.notes-toggle{grid-column:1/-1;justify-self:start;padding:4px 0;color:var(--accent-orange);font-size:11.5px;background:transparent;border:0;cursor:pointer}.notes-field{grid-column:1/-1}footer{display:flex;align-items:center;justify-content:flex-end;gap:8px;margin:0 -16px;padding:9px 16px 11px;background:color-mix(in srgb,var(--panel-bg-strong) 80%,transparent);border-top:1px solid var(--glass-divider);border-radius:0 0 12px 12px}footer button{min-width:64px;height:32px;padding:0 12px;color:var(--text-secondary);font-size:12px;background:transparent;border:1px solid var(--panel-border);border-radius:7px;cursor:pointer}.create-button{color:#fffaf2!important;background:var(--accent-orange)!important;border-color:transparent!important;box-shadow:0 6px 14px rgba(255,103,0,.18)}

.task-panel{background:var(--surface-glass, color-mix(in srgb,var(--panel-bg-strong) 78%,transparent));border:1px solid var(--panel-border);border-radius:8px;box-shadow:0 10px 34px #34433812;backdrop-filter:blur(18px);padding:18px 18px 0}header{padding-bottom:14px}header>div{display:grid;gap:5px}header strong{font-size:19px;font-weight:650}.panel-eyebrow{font-size:9px;letter-spacing:2px;color:var(--text-muted)}.task-form-grid{gap:12px}.full-width{grid-column:1/-1}.form-scroll{padding:16px 2px;scrollbar-width:thin;overscroll-behavior:contain}.form-scroll::-webkit-scrollbar{display:block;width:4px}.form-scroll::-webkit-scrollbar-thumb{background:#b6b9b366;border-radius:4px}.field{font-size:12px;gap:6px}.field input,.field select{height:36px;border-radius:5px}.map-selection{border-top:1px solid var(--panel-border);padding-top:14px;font-size:11px;color:var(--text-secondary)}.map-selection>div{display:flex;gap:6px;margin-top:7px}.map-selection button{flex:1;border:1px solid var(--panel-border);border-radius:5px;padding:8px 4px;color:var(--text-secondary);background:transparent;font:inherit;cursor:pointer}.map-selection button[aria-pressed=true]{border-color:#FB9966;color:var(--text-primary);background:color-mix(in srgb,#FB9966 12%,transparent)}footer{margin:0 -18px;padding:13px 18px;border-radius:0 0 8px 8px;gap:8px}footer>span{margin-right:auto;color:var(--text-muted);font-size:10px}footer button{height:36px;border-radius:5px}.create-button{background:#FB9966!important;color:#462918!important;box-shadow:0 4px 12px #fb996625}.priority-control button.active{background:color-mix(in srgb,#FB9966 16%,var(--panel-bg-strong));color:var(--text-primary)}
.task-panel{padding:10px 12px 0}header{padding-bottom:6px}header>div{gap:2px}header strong{font-size:16px}.form-scroll{padding:8px 2px}.task-form-grid{gap:7px 10px}.field{gap:3px;font-size:11px}.field input,.field select{height:31px}.map-selection{display:flex;align-items:center;justify-content:space-between;gap:10px;padding-top:7px}.map-selection>div{margin:0;flex:1}.map-selection button{padding:5px 3px}.priority-control legend{margin-bottom:3px}.priority-control button{height:25px}.notes-toggle{padding:2px 0}.field textarea{min-height:45px}footer{margin:0 -12px;padding:7px 12px}footer button{height:30px}
.task-panel{background:rgba(247,249,250,.46);border-color:rgba(255,255,255,.62);border-radius:15px;box-shadow:0 18px 52px #34433820;backdrop-filter:blur(24px) saturate(115%);-webkit-backdrop-filter:blur(24px) saturate(115%)}:global([data-theme='dark']) .task-panel{background:rgba(34,42,47,.52);border-color:rgba(255,255,255,.16)}.task-panel footer{background:rgba(255,255,255,.2);border-radius:0 0 15px 15px}:global([data-theme='dark']) .task-panel footer{background:rgba(19,25,29,.22)}
.task-form-grid{column-gap:6px}.field input[type=date],.field input[type=time]{padding-inline:5px;font-size:10px}.task-panel footer{gap:5px}.task-panel footer button{min-width:57px;padding-inline:8px}
.dispatch-robot-picker{position:relative}.robot-trigger{display:flex;align-items:center;gap:5px;width:100%;height:31px;min-width:0;padding:0 8px;color:var(--text-primary);background:color-mix(in srgb,var(--search-background) 80%,transparent);border:1px solid var(--icon-button-border);border-radius:7px;font:inherit;font-size:10px;text-align:left;cursor:pointer}.robot-trigger:focus-visible,.robot-options button:focus-visible{outline:2px solid var(--theme-primary);outline-offset:1px}.robot-trigger-name{flex:none;font-weight:600}.robot-trigger-state{overflow:hidden;flex:1;min-width:0;color:var(--text-secondary);text-overflow:ellipsis;white-space:nowrap}.robot-trigger-state:before{content:'·';margin-right:4px}.robot-trigger-battery{flex:none;color:var(--text-secondary)}.robot-trigger svg{flex:none;transition:transform .18s}.robot-trigger[aria-expanded=true] svg{transform:rotate(180deg)}.robot-options{display:grid;gap:3px;margin-top:5px;padding:5px;background:color-mix(in srgb,var(--panel-bg-strong) 82%,transparent);border:1px solid var(--panel-border);border-radius:9px;box-shadow:0 8px 20px #3443381c;backdrop-filter:blur(16px)}.robot-options button{display:flex;align-items:center;gap:6px;min-width:0;padding:7px 6px;color:var(--text-primary);background:transparent;border:0;border-radius:6px;font:inherit;font-size:10px;text-align:left;cursor:pointer}.robot-options button:hover,.robot-options button[aria-selected=true]{background:color-mix(in srgb,#fb9966 12%,transparent)}.robot-options i{flex:none;width:7px;height:7px;border-radius:50%}.robot-option-name{flex:none;font-weight:600}.robot-option-state{overflow:hidden;flex:1;min-width:0;color:var(--text-secondary);text-overflow:ellipsis;white-space:nowrap}.robot-options strong{flex:none;font-size:10px;font-weight:600}.task-panel footer{justify-content:flex-end}
.task-type-picker,.dispatch-time-picker{position:relative}.task-type-trigger{display:flex;align-items:center;justify-content:space-between;gap:4px;width:100%;height:31px;min-width:0;padding:0 8px;color:var(--text-primary);background:color-mix(in srgb,var(--search-background) 80%,transparent);border:1px solid var(--icon-button-border);border-radius:7px;font:inherit;font-size:10px;text-align:left;cursor:pointer}.task-type-trigger span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.task-type-trigger svg{flex:none}.task-type-options,.dispatch-time-options{position:absolute;z-index:30;top:100%;left:0;right:0;display:grid;gap:2px;max-height:205px;margin-top:4px;padding:5px;overflow:auto;color:var(--text-primary);background:color-mix(in srgb,var(--panel-bg-strong) 92%,transparent);border:1px solid var(--panel-border);border-radius:9px;box-shadow:0 10px 22px #34433825;backdrop-filter:blur(18px)}.task-type-options button,.dispatch-time-options button{min-height:27px;padding:5px 7px;color:inherit;background:transparent;border:0;border-radius:6px;font:inherit;font-size:10px;text-align:left;cursor:pointer}.task-type-options button:hover,.task-type-options button[aria-selected=true],.dispatch-time-options button:hover,.dispatch-time-options button[aria-selected=true]{background:color-mix(in srgb,#fb9966 15%,transparent)}.task-type-trigger:focus-visible,.task-type-options button:focus-visible,.dispatch-time-entry button:focus-visible,.dispatch-time-options button:focus-visible{outline:2px solid var(--theme-primary);outline-offset:1px}.dispatch-time-picker>label{color:var(--text-secondary)}.dispatch-time-entry{display:flex;align-items:center;height:31px;background:color-mix(in srgb,var(--search-background) 80%,transparent);border:1px solid var(--icon-button-border);border-radius:7px}.dispatch-time-entry:focus-within{border-color:var(--search-border-active);box-shadow:0 0 0 3px var(--search-focus-ring)}.dispatch-time-entry input{flex:1;width:100%;height:100%;min-width:0;padding:0 5px;border:0;background:transparent;box-shadow:none!important;font-size:10px}.dispatch-time-entry button{display:grid;place-items:center;flex:none;width:27px;height:27px;padding:0;color:var(--text-secondary);background:transparent;border:0;border-radius:6px;cursor:pointer}.dispatch-time-options{max-height:165px}.notes-field textarea{min-height:70px;padding:8px 9px;resize:vertical}.task-panel footer{background:transparent!important;border-top:0;box-shadow:none}
.task-type-options,.dispatch-time-options{background:#f8faf9}:global([data-theme='dark']) .task-type-options,:global([data-theme='dark']) .dispatch-time-options{background:#303735}
.field{font-size:13px}.field input,.field textarea,.task-type-trigger,.robot-trigger,.dispatch-time-entry input{font-size:12.5px}.task-type-options button,.robot-options button,.dispatch-time-options button{font-size:12px}.priority-control legend{font-size:12.5px}.priority-control button{font-size:12px}.task-panel footer button{font-size:12px}
.dispatch-location-picker{position:relative}.location-trigger{display:flex;align-items:center;justify-content:space-between;gap:5px;width:100%;height:34px;min-width:0;padding:0 9px;color:var(--text-primary);background:color-mix(in srgb,var(--search-background) 80%,transparent);border:1px solid var(--icon-button-border);border-radius:8px;font:inherit;font-size:12px;text-align:left;cursor:pointer}.location-trigger>span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.location-trigger svg{flex:none}.location-options{position:absolute;z-index:35;top:100%;left:0;right:0;display:grid;gap:3px;max-height:210px;margin-top:4px;padding:5px;overflow:auto;color:var(--text-primary);background:#f8faf9;border:1px solid var(--panel-border);border-radius:10px;box-shadow:0 10px 22px #34433825}.location-options button{min-height:30px;padding:5px 8px;color:inherit;background:transparent;border:0;border-radius:7px;font:inherit;font-size:12px;text-align:left;cursor:pointer}.location-trigger:focus-visible,.location-options button:focus-visible{outline:2px solid var(--theme-primary);outline-offset:1px}:global([data-theme='dark']) .location-options{background:#303735}
.location-options button:hover,.location-options button[aria-selected=true]{background:color-mix(in srgb,#fb9966 15%,transparent)}
.priority-control button.active{background:color-mix(in srgb,var(--priority-color) 20%,var(--panel-bg-strong));box-shadow:none}
.priority-control button:hover{background:color-mix(in srgb,var(--priority-color) 18%,var(--panel-bg-strong))}
.task-panel{height:auto;grid-template-rows:auto auto}
.task-panel form{grid-template-rows:auto auto}
.form-scroll{overflow:visible;scrollbar-width:none}
.form-scroll::-webkit-scrollbar{display:none}
.required-capabilities{display:grid;gap:5px;padding:7px 9px;color:#705f35;background:#fff8df;border:1px solid #ebdfb9;border-radius:8px;font-size:11px}
.required-capabilities>div{display:flex;flex-wrap:wrap;gap:5px}
.required-capabilities>div span{padding:3px 8px;border-radius:5px;font-size:11px}
.required-capabilities>div span{color:#426d53;background:#e0efe3}
.task-form-grid .field>span:first-child,.task-form-grid .field>label,.priority-control legend,.required-capabilities>span{font-weight:600;letter-spacing:.01em}
.task-form-grid .field>span:first-child,.task-form-grid .field>label,.priority-control legend{color:var(--text-secondary)}
.task-type-trigger,.robot-trigger,.location-trigger,.dispatch-time-entry input,.field input,.field textarea{font-weight:400}
.priority-control button.active{font-weight:600}
.priority-control button[data-priority=high].active{color:#783519;background:#f5c39f}
.priority-control button[data-priority=emergency].active{color:#fff;background:#a94453}
.priority-control button[data-priority=high]:not(.active):hover{background:#fbe0c9}
.priority-control button[data-priority=emergency]:not(.active):hover{color:#8d3444;background:#f5cbd2}
:global([data-theme='dark']) .required-capabilities{color:#e4d3a5;background:#463f2b;border-color:#6d5d36}
:global([data-theme='dark']) .required-capabilities>div span{color:#dcefe0;background:#3d5c47}
.task-panel footer button{transition:background-color .18s,border-color .18s,color .18s,box-shadow .18s,transform .18s}
.task-panel footer button:not(.create-button):hover{color:var(--text-primary);background:color-mix(in srgb,#fb9966 10%,var(--panel-bg-strong));border-color:#fb9966}
.task-panel footer .create-button:hover{background:#f8874d!important;box-shadow:0 6px 16px #fb99664d;transform:translateY(-1px)}
.task-panel footer button:focus-visible{outline:2px solid var(--theme-primary);outline-offset:2px}
</style>
