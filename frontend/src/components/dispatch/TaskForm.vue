<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { Ban, CalendarDays, ChevronLeft, ChevronRight, ChevronDown, Clock3 } from '@lucide/vue'
import { localeTag, t, translateLocation, translateTask } from '@/i18n/index.js'
import { taskPriorityColor } from '@/config/taskPriorityColors.js'
import { TASK_LOCATION_IDS, TASK_TYPE_BY_LABEL, TASK_TYPE_LABELS } from '@/config/taskTypes.js'
import { dispatchWaypointLabels } from '@/config/dispatchDestinations.js'

const props = defineProps({
  submitting: { type: Boolean, default: false },
  locations: { type: Array, required: true },
  destination: { type: String, default: '' },
  source: { type: String, default: 'pharmacy' },
  date: { type: String, required: true },
})
const emit = defineEmits(['submit', 'update:destination', 'update:source', 'update:task-type'])
const taskTypes = TASK_TYPE_LABELS
const priorities = [{ value: 'low' }, { value: 'normal' }, { value: 'high' }, { value: 'emergency' }]
const DEFAULT_DURATION_SECONDS = 12 * 60
const taskTypeOpen = ref(false)
const taskTypePicker = ref(null)
const sourcePickerOpen = ref(false)
const destinationPickerOpen = ref(false)
const sourcePicker = ref(null)
const destinationPicker = ref(null)
const locationMenu = ref(null)
const locationMenuStyle = ref({})
const openLocationField = computed(() => sourcePickerOpen.value ? 'source' : destinationPickerOpen.value ? 'destination' : null)
const localDate = (now) => `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`
const localTime = (now) => `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}`
const nextStart = () => new Date(Date.now() + 60_000)
const initialStart = nextStart()
const timeText = ref(localTime(initialStart))
const timePickerOpen = ref(false)
const timeEntry = ref(null)
const timeMenu = ref(null)
const timeMenuStyle = ref({})
const hours = Array.from({ length: 24 }, (_, index) => String(index).padStart(2, '0'))
const minutes = Array.from({ length: 60 }, (_, index) => String(index).padStart(2, '0'))
const validationError = ref('')
const errorSummary = ref(null)
const datePickerOpen = ref(false)
const datePicker = ref(null)
const dateTrigger = ref(null)
const calendarMenu = ref(null)
const calendarMenuStyle = ref({})
const calendarMonth = ref(new Date())
const positionFloatingMenu = (anchor, menu, preferredWidth) => {
  if (!anchor || !menu) return {}
  const anchorRect = anchor.getBoundingClientRect()
  const menuRect = menu.getBoundingClientRect()
  const margin = 8
  const width = Math.min(preferredWidth ?? anchorRect.width, window.innerWidth - margin * 2)
  const contentHeight = Math.max(menu.scrollHeight, menuRect.height)
  const spaceAbove = Math.max(0, anchorRect.top - margin)
  const spaceBelow = Math.max(0, window.innerHeight - anchorRect.bottom - margin)
  const openAbove = spaceBelow < contentHeight && spaceAbove > spaceBelow
  const availableHeight = Math.max(120, (openAbove ? spaceAbove : spaceBelow) - margin)
  const height = Math.min(contentHeight || 240, availableHeight)
  const left = Math.max(margin, Math.min(anchorRect.left, window.innerWidth - width - margin))
  const top = openAbove
    ? Math.max(margin, anchorRect.top - height - margin)
    : Math.min(anchorRect.bottom + margin, window.innerHeight - height - margin)
  return { top: `${top}px`, left: `${left}px`, width: `${width}px`, maxHeight: `${availableHeight}px` }
}
const updateFloatingMenus = () => {
  if (datePickerOpen.value) calendarMenuStyle.value = positionFloatingMenu(dateTrigger.value, calendarMenu.value, 280)
  if (timePickerOpen.value) timeMenuStyle.value = positionFloatingMenu(timeEntry.value, timeMenu.value, 152)
  const field = openLocationField.value
  const trigger = (field === 'source' ? sourcePicker.value : destinationPicker.value)?.querySelector('button')
  if (field && trigger) {
    const rect = trigger.getBoundingClientRect()
    locationMenuStyle.value = {
      top: `${rect.bottom + 4}px`,
      left: `${rect.left}px`,
      width: `${rect.width}px`,
      maxHeight: `${Math.max(0, Math.min(180, window.innerHeight - rect.bottom - 12))}px`,
    }
  }
}
const parseTimeText = (value) => {
  const text = value.trim().replace(/^(\d{2})(\d{2})$/, '$1:$2')
  const match = /^([01]?\d|2[0-3]):([0-5]\d)$/.exec(text)
  return match ? `${match[1].padStart(2,'0')}:${match[2]}:00` : null
}
watch(openLocationField, async field => { if (field) { await nextTick(); updateFloatingMenus() } })
const normalizeTimeText = () => {
  const time = parseTimeText(timeText.value)
  if (time) timeText.value = time.slice(0,5)
}
const selectedTime = computed(() => parseTimeText(timeText.value)?.slice(0, 5) || '')
const chooseTimePart = (index, value) => {
  const parts = (selectedTime.value || localTime(nextStart())).split(':')
  parts[index] = value
  timeText.value = parts.join(':')
}
const toggleTimePicker = async () => {
  timePickerOpen.value = !timePickerOpen.value
  if (!timePickerOpen.value) return
  datePickerOpen.value = false
  if (!selectedTime.value) timeText.value = localTime(nextStart())
  await nextTick()
  updateFloatingMenus()
  timeMenu.value?.querySelectorAll('[aria-selected="true"]').forEach(option => {
    const column = option.parentElement
    column.scrollTop = option.offsetTop - (column.clientHeight - option.offsetHeight) / 2
  })
}
const selectLocation = (field, value) => {
  if (field === 'source') { sourceValue.value = value; sourcePickerOpen.value = false }
  else { destinationValue.value = value; destinationPickerOpen.value = false }
}
const onOutsidePointer = (event) => {
  if (!taskTypePicker.value?.contains(event.target)) taskTypeOpen.value = false
  if (!datePicker.value?.contains(event.target) && !calendarMenu.value?.contains(event.target)) datePickerOpen.value = false
  if (!timeEntry.value?.contains(event.target) && !timeMenu.value?.contains(event.target)) timePickerOpen.value = false
  if (!locationMenu.value?.contains(event.target)) {
    if (!sourcePicker.value?.contains(event.target)) sourcePickerOpen.value = false
    if (!destinationPicker.value?.contains(event.target)) destinationPickerOpen.value = false
  }
}
onMounted(() => {
  document.addEventListener('pointerdown', onOutsidePointer)
  document.addEventListener('scroll', updateFloatingMenus, true)
  window.addEventListener('resize', updateFloatingMenus)
})
onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', onOutsidePointer)
  document.removeEventListener('scroll', updateFloatingMenus, true)
  window.removeEventListener('resize', updateFloatingMenus)
})

const makeDefaults = (start) => ({
  type: '藥品配送',
  date: props.date === localDate(new Date()) ? localDate(start) : props.date,
  priority: 'normal', note: '',
})
const form = reactive(makeDefaults(initialStart))
const sourceValue = computed({ get: () => props.source, set: (value) => emit('update:source', value) })
const destinationValue = computed({ get: () => props.destination, set: (value) => emit('update:destination', value) })
const allowedLocations = computed(() => TASK_LOCATION_IDS[TASK_TYPE_BY_LABEL[form.type]])
const availableLocationIds = computed(() => new Set(props.locations))
const allowedSources = computed(() => allowedLocations.value.sources.filter(id => availableLocationIds.value.has(id)))
const allowedDestinations = computed(() => allowedLocations.value.destinations.filter(id => availableLocationIds.value.has(id)))
watch(() => form.type, () => {
  emit('update:task-type', TASK_TYPE_BY_LABEL[form.type])
  sourceValue.value = allowedSources.value[0] || ''
  destinationValue.value = allowedDestinations.value[0] || ''
})
watch(() => props.locations, () => {
  if (!allowedSources.value.includes(sourceValue.value)) sourceValue.value = allowedSources.value[0] || ''
  if (!allowedDestinations.value.includes(destinationValue.value)) destinationValue.value = allowedDestinations.value[0] || ''
})

watch(() => props.date, (value) => { form.date = value })
const calendarHeading = computed(()=>new Intl.DateTimeFormat(localeTag.value,{year:'numeric',month:'long'}).format(calendarMonth.value))
const weekdays = computed(()=>Array.from({length:7},(_,i)=>new Intl.DateTimeFormat(localeTag.value,{weekday:'short'}).format(new Date(2026,0,4+i))))
const calendarDays = computed(()=>{
  const month = calendarMonth.value
  const first = new Date(month.getFullYear(),month.getMonth(),1)
  return Array.from({length:42},(_,i)=>{
    const date = new Date(first.getFullYear(),first.getMonth(),1-first.getDay()+i)
    return {value:localDate(date),day:date.getDate(),outside:date.getMonth()!==month.getMonth(),today:localDate(date)===localDate(new Date())}
  })
})
const toggleCalendar = () => {
  if (!datePickerOpen.value) calendarMonth.value = new Date(`${form.date}T12:00:00`)
  datePickerOpen.value = !datePickerOpen.value
  if (datePickerOpen.value) timePickerOpen.value = false
}
const shiftMonth = (offset) => { calendarMonth.value = new Date(calendarMonth.value.getFullYear(),calendarMonth.value.getMonth()+offset,1) }
const selectDate = (value) => { form.date = value; datePickerOpen.value = false }
watch(datePickerOpen, async (open) => {
  if (!open) { calendarMenuStyle.value = {}; return }
  await nextTick()
  updateFloatingMenus()
})

const reset = () => {
  const now = nextStart()
  Object.assign(form, makeDefaults(now))
  validationError.value = ''
  sourceValue.value = 'pharmacy'
  destinationValue.value = 'ward_a_2'
  sourcePickerOpen.value = false
  destinationPickerOpen.value = false
  form.date = localDate(now)
  timeText.value = localTime(now)
  timePickerOpen.value = false
  taskTypeOpen.value = false
  datePickerOpen.value = false
}
defineExpose({ reset })
const submit = async () => {
  if (props.submitting) return
  const startTime = parseTimeText(timeText.value)
  const scheduled = startTime ? new Date(`${form.date}T${startTime}`) : null
  validationError.value = !startTime ? 'invalidTime'
    : !scheduled || !Number.isFinite(scheduled.getTime()) || scheduled <= new Date() ? 'futureTime'
    : sourceValue.value === destinationValue.value ? 'differentLocations'
    : !allowedSources.value.includes(sourceValue.value) || !allowedDestinations.value.includes(destinationValue.value) ? 'chooseLocations' : ''
  if (validationError.value) {
    await nextTick()
    errorSummary.value?.focus()
    return
  }
  emit('submit', {
    robotId: null, title: form.type, type: form.type,
    taskType: TASK_TYPE_BY_LABEL[form.type],
    source: sourceValue.value, destination: destinationValue.value, date: form.date,
    startTime, durationSeconds: DEFAULT_DURATION_SECONDS,
    priority: form.priority, note: form.note || null,
    scheduledAt: new Date(`${form.date}T${startTime}`).toISOString(),
  })
}
</script>

<template>
  <section class="task-panel" :aria-label="t('dispatchForm.title')">
    <header><div><span class="panel-eyebrow">{{ t('dispatchForm.eyebrow') }}</span><strong>{{ t('dispatchForm.title') }}</strong></div></header>
    <form novalidate :aria-busy="submitting" @submit.prevent="submit">
      <fieldset class="task-form-fields" :disabled="submitting">
      <div class="form-scroll task-form-grid">
        <p class="form-guidance full-width"><span class="guidance-required"><span class="guidance-required-marker">*</span> {{ t('dispatchUx.requiredLabel') }}</span><span class="guidance-time">{{ t('dispatchUx.localTimeHint') }}</span></p>
        <p v-if="validationError" ref="errorSummary" class="form-validation full-width" role="alert" tabindex="-1">{{ t(`dispatchUx.${validationError}`) }}</p>
        <div ref="taskTypePicker" class="field task-type-picker full-width" @keydown.esc.stop="taskTypeOpen=false"><span>{{ t('dispatchForm.type') }} <span class="required-marker" aria-hidden="true">＊</span></span><button type="button" class="task-type-trigger" :aria-label="t('dispatchForm.type')" :aria-expanded="taskTypeOpen" aria-haspopup="listbox" @click="taskTypeOpen=!taskTypeOpen"><span>{{ translateTask(form.type) }}</span><ChevronDown :size="14" /></button><div v-if="taskTypeOpen" class="task-type-options" role="listbox" :aria-label="t('dispatchForm.type')"><button v-for="type in taskTypes" :key="type" type="button" role="option" :aria-selected="form.type===type" @click="form.type=type;taskTypeOpen=false">{{ translateTask(type) }}</button></div></div>

        <div class="dispatch-location-fields">
          <div ref="sourcePicker" class="field dispatch-location-picker" @keydown.esc.stop="sourcePickerOpen=false"><span>{{ t('dispatchForm.source') }} <span class="required-marker" aria-hidden="true">＊</span></span><button type="button" class="location-trigger" :class="{ 'is-fixed': allowedSources.length === 1 }" :disabled="allowedSources.length === 1" :aria-label="t('dispatchForm.source')" :aria-expanded="sourcePickerOpen" aria-haspopup="listbox" @click="sourcePickerOpen=!sourcePickerOpen;destinationPickerOpen=false"><span>{{ translateLocation(dispatchWaypointLabels[sourceValue] || sourceValue) }}</span><Ban v-if="allowedSources.length === 1" :size="15" aria-hidden="true" /><ChevronDown v-else :size="15" /></button></div>
          <div ref="destinationPicker" class="field dispatch-location-picker" @keydown.esc.stop="destinationPickerOpen=false"><span>{{ t('dispatchForm.destination') }} <span class="required-marker" aria-hidden="true">＊</span></span><button type="button" class="location-trigger" :class="{ 'is-fixed': allowedDestinations.length === 1 }" :disabled="allowedDestinations.length === 1" :aria-label="t('dispatchForm.destination')" :aria-expanded="destinationPickerOpen" aria-haspopup="listbox" @click="destinationPickerOpen=!destinationPickerOpen;sourcePickerOpen=false"><span>{{ translateLocation(dispatchWaypointLabels[destinationValue] || destinationValue) }}</span><Ban v-if="allowedDestinations.length === 1" :size="15" aria-hidden="true" /><ChevronDown v-else :size="15" /></button></div>
        </div>

        <div ref="datePicker" class="field dispatch-date-picker" @keydown.esc.stop="datePickerOpen=false"><span>{{ t('dispatchForm.date') }} <span class="required-marker" aria-hidden="true">＊</span></span><button ref="dateTrigger" class="date-trigger" type="button" :aria-label="t('dispatchForm.date')" :aria-expanded="datePickerOpen" aria-haspopup="dialog" @click="toggleCalendar"><span>{{ form.date.replaceAll('-',' / ') }}</span><CalendarDays :size="14" /></button></div>
        <div class="field">
          <label for="dispatch-start-time">{{ t('dispatchForm.start') }} <span class="required-marker" aria-hidden="true">＊</span></label>
          <div ref="timeEntry" class="dispatch-time-entry" @keydown.esc.stop="timePickerOpen=false">
            <input id="dispatch-start-time" v-model.trim="timeText" type="text" inputmode="numeric" maxlength="5" placeholder="HH:MM" required @blur="normalizeTimeText">
            <button type="button" :aria-label="t('dispatchForm.chooseTime')" :aria-expanded="timePickerOpen" aria-haspopup="dialog" @click="toggleTimePicker"><Clock3 :size="14" /></button>
          </div>
        </div>

        <fieldset class="priority-control full-width"><legend>{{ t('dispatchForm.priority') }} <span class="required-marker" aria-hidden="true">＊</span></legend><div><button v-for="priority in priorities" :key="priority.value" type="button" :data-priority="priority.value" :style="{ '--priority-color': taskPriorityColor(priority.value) }" :class="{ active: form.priority === priority.value }" :aria-pressed="form.priority === priority.value" @click="form.priority=priority.value">{{ t(`priority.${priority.value}`) }}</button></div></fieldset>
        <label class="field notes-field"><span>{{ t('dispatchForm.note') }}</span><textarea v-model.trim="form.note" rows="4" :placeholder="t('dispatchForm.notePlaceholder')"></textarea></label>
      </div>
      </fieldset>
      <Teleport to="body">
        <div v-if="openLocationField" ref="locationMenu" class="location-options" role="listbox"
          :aria-label="t(`dispatchForm.${openLocationField}`)" :style="locationMenuStyle"
          @keydown.esc.stop="sourcePickerOpen=false;destinationPickerOpen=false">
          <button v-for="location in openLocationField === 'source' ? allowedSources : allowedDestinations"
            :key="location" type="button" role="option"
            :aria-selected="(openLocationField === 'source' ? sourceValue : destinationValue) === location"
            @click="selectLocation(openLocationField, location)">
            {{ translateLocation(dispatchWaypointLabels[location] || location) }}
          </button>
        </div>
        <div v-if="datePickerOpen" ref="calendarMenu" class="dispatch-calendar is-floating" role="dialog" :aria-label="t('dispatchForm.date')" :style="calendarMenuStyle" @keydown.esc.stop="datePickerOpen=false">
          <div class="calendar-heading"><button type="button" :disabled="submitting" :aria-label="t('dispatch.previousMonth')" @click="shiftMonth(-1)"><ChevronLeft :size="16" /></button><strong>{{ calendarHeading }}</strong><button type="button" :disabled="submitting" :aria-label="t('dispatch.nextMonth')" @click="shiftMonth(1)"><ChevronRight :size="16" /></button></div>
          <div class="calendar-grid"><span v-for="(day,index) in weekdays" :key="index" class="calendar-weekday">{{ day }}</span><button v-for="day in calendarDays" :key="day.value" type="button" :disabled="submitting" :data-date="day.value" :class="{outside:day.outside,today:day.today}" :aria-label="day.value" :aria-pressed="form.date===day.value" @click="selectDate(day.value)">{{ day.day }}</button></div>
        </div>
        <div v-if="timePickerOpen" ref="timeMenu" class="dispatch-time-options" role="dialog" :aria-label="t('dispatchForm.chooseTime')" :style="timeMenuStyle" @keydown.esc.stop="timePickerOpen=false">
          <div class="time-scroll-column" role="listbox" :aria-label="t('dispatch.hours')">
            <button v-for="hour in hours" :key="hour" type="button" role="option" :disabled="submitting" :aria-selected="selectedTime.slice(0, 2) === hour" @click="chooseTimePart(0, hour)">{{ hour }}</button>
          </div>
          <span aria-hidden="true">:</span>
          <div class="time-scroll-column" role="listbox" :aria-label="t('dispatch.minutes')">
            <button v-for="minute in minutes" :key="minute" type="button" role="option" :disabled="submitting" :aria-selected="selectedTime.slice(3, 5) === minute" @click="chooseTimePart(1, minute)">{{ minute }}</button>
          </div>
        </div>
      </Teleport>
      <footer><button type="button" :disabled="submitting" @click="reset">{{ t('dispatchUx.reset') }}</button><button type="submit" class="create-button" :disabled="submitting">{{ t(submitting ? 'dispatchUx.creating' : 'dispatchForm.create') }}</button></footer>
    </form>
  </section>
</template>

<style scoped>
.task-panel{box-sizing:border-box;display:grid;grid-template-rows:auto minmax(0,1fr);width:100%;max-width:none;height:100%;min-height:0;padding:12px 16px 0;color:var(--text-primary);background:rgba(246,244,239,.78);border:1px solid rgba(255,255,255,.58);border-radius:12px;box-shadow:0 18px 45px rgba(66,59,48,.10);backdrop-filter:blur(22px) saturate(115%);-webkit-backdrop-filter:blur(22px) saturate(115%)}:global([data-theme='dark']) .task-panel{background:rgba(61,65,62,.88);border-color:rgba(255,255,255,.12)}
header{display:flex;align-items:center;justify-content:space-between;padding-bottom:7px;border-bottom:1px solid var(--glass-divider)}header strong{font-size:15px}header button{width:27px;height:27px;color:var(--text-muted);font-size:19px;background:transparent;border:0;border-radius:6px;cursor:pointer}header button:hover{background:var(--icon-button-hover)}form{display:grid;grid-template-rows:minmax(0,1fr) auto;min-height:0}.form-scroll{min-height:0;padding:8px 2px;overflow-y:auto;scrollbar-width:none}.form-scroll::-webkit-scrollbar{display:none}.task-form-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));align-content:start;gap:6px 14px}.field{display:grid;gap:4px;min-width:0;color:var(--text-secondary);font-size:11.5px}.field input,.field select,.field textarea{box-sizing:border-box;width:100%;min-width:0;height:32px;padding:5px 9px;color:var(--text-primary);background:color-mix(in srgb,var(--search-background) 80%,transparent);border:1px solid var(--icon-button-border);border-radius:7px;font:inherit;outline:0}.field textarea{height:auto;min-height:56px;resize:vertical}.field input:focus,.field select:focus,.field textarea:focus{border-color:var(--search-border-active);box-shadow:0 0 0 3px var(--search-focus-ring)}
.computed-time{display:grid;gap:4px;color:var(--text-secondary);font-size:11.5px}.computed-time strong{display:flex;align-items:center;height:32px;color:var(--text-primary);font-size:13px;font-variant-numeric:tabular-nums}
.priority-control{margin:0;padding:0;border:0}.priority-control legend{margin-bottom:5px;color:var(--text-secondary);font-size:11.5px}.priority-control>div{display:grid;grid-template-columns:repeat(4,1fr);padding:0;background:color-mix(in srgb,var(--progress-track) 74%,transparent);border-radius:7px}.priority-control button{height:29px;color:var(--text-secondary);font-size:11px;background:transparent;border:0;border-radius:5px;cursor:pointer}.priority-control button.active{color:var(--text-primary);background:var(--panel-bg-strong);box-shadow:0 2px 7px rgba(65,58,48,.09)}.notes-toggle{grid-column:1/-1;justify-self:start;padding:4px 0;color:var(--accent-orange);font-size:11.5px;background:transparent;border:0;cursor:pointer}.notes-field{grid-column:1/-1}footer{display:flex;align-items:center;justify-content:flex-end;gap:8px;margin:0 -16px;padding:9px 16px 11px;background:color-mix(in srgb,var(--panel-bg-strong) 80%,transparent);border-top:1px solid var(--glass-divider);border-radius:0 0 12px 12px}footer button{min-width:64px;height:32px;padding:0 12px;color:var(--text-secondary);font-size:12px;background:transparent;border:1px solid var(--panel-border);border-radius:7px;cursor:pointer}.create-button{color:#fffaf2!important;background:var(--accent-orange)!important;border-color:transparent!important;box-shadow:0 6px 14px rgba(255,103,0,.18)}

.task-panel{background:var(--surface-glass, color-mix(in srgb,var(--panel-bg-strong) 78%,transparent));border:1px solid var(--panel-border);border-radius:8px;box-shadow:0 10px 34px #34433812;backdrop-filter:blur(18px);padding:18px 18px 0}header{padding-bottom:14px}header>div{display:grid;gap:5px}header strong{font-size:19px;font-weight:650}.panel-eyebrow{font-size:9px;letter-spacing:2px;color:var(--text-muted)}.task-form-grid{gap:12px}.full-width{grid-column:1/-1}.form-scroll{padding:16px 2px;scrollbar-width:thin;overscroll-behavior:contain}.form-scroll::-webkit-scrollbar{display:block;width:4px}.form-scroll::-webkit-scrollbar-thumb{background:#b6b9b366;border-radius:4px}.field{font-size:12px;gap:6px}.field input,.field select{height:36px;border-radius:5px}.map-selection{border-top:1px solid var(--panel-border);padding-top:14px;font-size:11px;color:var(--text-secondary)}.map-selection>div{display:flex;gap:6px;margin-top:7px}.map-selection button{flex:1;border:1px solid var(--panel-border);border-radius:5px;padding:8px 4px;color:var(--text-secondary);background:transparent;font:inherit;cursor:pointer}.map-selection button[aria-pressed=true]{border-color:#FB9966;color:var(--text-primary);background:color-mix(in srgb,#FB9966 12%,transparent)}footer{margin:0 -18px;padding:13px 18px;border-radius:0 0 8px 8px;gap:8px}footer>span{margin-right:auto;color:var(--text-muted);font-size:10px}footer button{height:36px;border-radius:5px}.create-button{background:#FB9966!important;color:#462918!important;box-shadow:0 4px 12px #fb996625}.priority-control button.active{background:color-mix(in srgb,#FB9966 16%,var(--panel-bg-strong));color:var(--text-primary)}
.task-panel{padding:10px 12px 0}header{padding-bottom:6px}header>div{gap:2px}header strong{font-size:16px}.form-scroll{padding:8px 2px}.task-form-grid{gap:7px 10px}.field{gap:3px;font-size:11px}.field input,.field select{height:31px}.map-selection{display:flex;align-items:center;justify-content:space-between;gap:10px;padding-top:7px}.map-selection>div{margin:0;flex:1}.map-selection button{padding:5px 3px}.priority-control legend{margin-bottom:3px}.priority-control button{height:25px}.notes-toggle{padding:2px 0}.field textarea{min-height:45px}footer{margin:0 -12px;padding:7px 12px}footer button{height:30px}
.task-panel{background:rgba(247,249,250,.46);border-color:rgba(255,255,255,.62);border-radius:15px;box-shadow:0 18px 52px #34433820;backdrop-filter:blur(24px) saturate(115%);-webkit-backdrop-filter:blur(24px) saturate(115%)}:global([data-theme='dark']) .task-panel{background:rgba(34,42,47,.52);border-color:rgba(255,255,255,.16)}.task-panel footer{background:rgba(255,255,255,.2);border-radius:0 0 15px 15px}:global([data-theme='dark']) .task-panel footer{background:rgba(19,25,29,.22)}
.task-form-grid{column-gap:6px}.field input[type=date],.field input[type=time]{padding-inline:5px;font-size:10px}.task-panel footer{gap:5px}.task-panel footer button{min-width:57px;padding-inline:8px}
.task-type-picker{position:relative}.task-type-trigger{display:flex;align-items:center;justify-content:space-between;gap:4px;width:100%;height:31px;min-width:0;padding:0 8px;color:var(--text-primary);background:color-mix(in srgb,var(--search-background) 80%,transparent);border:1px solid var(--icon-button-border);border-radius:7px;font:inherit;font-size:10px;text-align:left;cursor:pointer}.task-type-trigger span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.task-type-trigger svg{flex:none}.task-type-options{position:absolute;z-index:30;top:100%;left:0;right:0;display:grid;gap:2px;max-height:205px;margin-top:4px;padding:5px;overflow:auto;color:var(--text-primary);background:color-mix(in srgb,var(--panel-bg-strong) 92%,transparent);border:1px solid var(--panel-border);border-radius:9px;box-shadow:0 10px 22px #34433825;backdrop-filter:blur(18px)}.task-type-options button{min-height:27px;padding:5px 7px;color:inherit;background:transparent;border:0;border-radius:6px;font:inherit;font-size:10px;text-align:left;cursor:pointer}.task-type-options button:hover,.task-type-options button[aria-selected=true]{background:color-mix(in srgb,#fb9966 15%,transparent)}.task-type-trigger:focus-visible,.task-type-options button:focus-visible{outline:2px solid var(--theme-primary);outline-offset:1px}.notes-field textarea{min-height:70px;padding:8px 9px;resize:vertical}.task-panel footer{background:transparent!important;border-top:0;box-shadow:none}
.task-type-options{background:#f8faf9}:global([data-theme='dark']) .task-type-options{background:#303735}
.field{font-size:13px}.field input,.field textarea,.task-type-trigger{font-size:12.5px}.task-type-options button,.robot-options button{font-size:12px}.priority-control legend{font-size:12.5px}.priority-control button{font-size:12px}.task-panel footer button{font-size:12px}
.dispatch-location-picker{position:relative}.location-trigger{display:flex;align-items:center;justify-content:space-between;gap:5px;width:100%;height:34px;min-width:0;padding:0 9px;color:var(--text-primary);background:color-mix(in srgb,var(--search-background) 80%,transparent);border:1px solid var(--icon-button-border);border-radius:8px;font:inherit;font-size:12px;text-align:left;cursor:pointer}.location-trigger>span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.location-trigger svg{flex:none}.location-options{position:fixed;z-index:1100;box-sizing:border-box;display:grid;gap:3px;max-height:210px;margin-top:4px;padding:5px;overflow:auto;color:var(--text-primary);background:var(--dispatch-popover-background);border:1px solid var(--dispatch-control-border);border-radius:10px;box-shadow:0 10px 22px #34433825}.location-options button{min-height:30px;padding:5px 8px;color:inherit;background:transparent;border:0;border-radius:7px;font:inherit;font-size:12px;text-align:left;cursor:pointer}.location-trigger:focus-visible,.location-options button:focus-visible{outline:2px solid var(--theme-primary);outline-offset:1px}:global([data-theme='dark']) .location-options{background:#303735}
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
.task-type-trigger,.location-trigger,.field input,.field textarea{font-weight:400}
.location-trigger.is-fixed:disabled{color:var(--text-secondary);background:color-mix(in srgb,var(--text-muted) 10%,var(--search-background));border-color:var(--panel-border);opacity:1;cursor:not-allowed}.location-trigger.is-fixed:disabled svg{color:var(--text-muted)}
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

<style scoped>
.required-marker { color: var(--dispatch-required-marker); }
</style>

<style scoped>
.dispatch-date-picker{position:relative}.date-trigger{display:flex;align-items:center;justify-content:space-between;gap:6px;width:100%;height:31px;padding:0 8px;color:var(--text-primary);background:color-mix(in srgb,var(--search-background) 80%,transparent);border:1px solid var(--icon-button-border);border-radius:7px;font:inherit;font-size:12.5px;cursor:pointer}
.dispatch-calendar{position:absolute;z-index:40;top:100%;left:0;width:260px;max-width:calc(100vw - 72px);box-sizing:border-box;margin-top:5px;padding:12px;color:var(--text-primary);background:var(--panel-bg-strong,#fff);border:1px solid var(--panel-border);border-radius:12px;box-shadow:0 10px 28px #34433825}.calendar-heading{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px}.calendar-heading strong{font-size:13px}.dispatch-calendar button{color:inherit;background:transparent;border:0;border-radius:6px;font:inherit;cursor:pointer}.calendar-heading button{display:grid;place-items:center;width:28px;height:28px}.calendar-grid{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:3px;text-align:center}.calendar-weekday{padding:5px 0;color:var(--text-muted);font-size:10px}.calendar-grid button{height:28px;font-size:12px}.calendar-grid button.outside{color:var(--text-muted);opacity:.55}.calendar-grid button.today{font-weight:700;color:#ba5424}.dispatch-calendar button:hover{background:#ffe4d4;color:#813c1c}.calendar-grid button[aria-pressed=true]{background:#fb9966;color:#462918;opacity:1}.date-trigger:focus-visible,.dispatch-calendar button:focus-visible{outline:2px solid #fb9966;outline-offset:1px}
.dispatch-calendar.is-floating{position:fixed;z-index:1100;top:auto;right:auto;bottom:auto;left:auto;margin:0;max-width:calc(100vw - 16px);overflow:auto}
.form-guidance{margin-bottom:4px}
</style>

<style scoped>
.task-form-fields{display:grid;min-height:0;min-width:0;margin:0;padding:0;border:0}
.form-guidance,.field-hint,.required-capabilities p{margin:0;color:var(--text-secondary);font-size:11px;line-height:1.6;font-weight:400}
.required-capabilities{display:block;padding:10px 12px;color:var(--dispatch-hint-text,#705f35);background:var(--dispatch-hint-bg,rgba(255,245,203,.66));border:1px solid var(--dispatch-hint-border,rgba(210,180,94,.38));backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px)}
.required-capabilities summary{display:flex;align-items:center;gap:7px;min-height:22px;list-style:none;cursor:pointer;font-weight:600;line-height:1.5}
.required-capabilities summary::-webkit-details-marker{display:none}.required-capabilities summary::marker{content:''}
.required-capabilities summary svg{flex:0 0 14px;transition:transform .15s}.required-capabilities[open] summary svg{transform:rotate(90deg)}
.required-capabilities summary:focus-visible{outline:2px solid var(--theme-primary);outline-offset:3px;border-radius:3px}
.required-capabilities p{margin-top:7px;color:inherit}.required-capabilities[open]>div{margin-top:8px;align-items:center}
.form-guidance{display:flex;flex-wrap:wrap;align-items:baseline;gap:4px 10px}
.guidance-required{color:var(--dispatch-guidance-required)}.guidance-time{color:var(--dispatch-guidance-time)}.guidance-required-marker{color:var(--dispatch-required-marker);font-weight:700}
.required-capabilities{color:var(--dispatch-hint-text);background:var(--dispatch-hint-bg);border-color:var(--dispatch-hint-border)}
.required-capabilities>div span{color:var(--dispatch-popover-hover-text);background:var(--dispatch-popover-hover-background)}
@media(prefers-reduced-motion:reduce){.required-capabilities summary svg{transition:none}}
.form-validation{margin:0;padding:10px;color:#9b2836;background:#fff0f0;border:1px solid #d99aa3;border-radius:7px;font-size:12px;line-height:1.6}
button:disabled{opacity:.55;cursor:not-allowed}
.task-form-fields:disabled{opacity:.75}
:global([data-theme='dark']) .form-validation{color:#ffd3d8;background:#512b33}
</style>

<style scoped>
.task-panel{color:var(--text-primary)}
.task-panel :is(.task-type-trigger,.location-trigger,.date-trigger,.field input,.field textarea){
  color:var(--dispatch-control-text);
  background:var(--dispatch-control-background);
  border-color:var(--dispatch-control-border);
}
.task-panel :is(.field>span:first-child,.field>label,.priority-control legend){
  color:var(--dispatch-control-label);
}
.task-panel .location-trigger.is-fixed:disabled{
  color:var(--dispatch-control-disabled-text);
  background:var(--dispatch-control-disabled-background);
  border-color:var(--dispatch-control-disabled-border);
  opacity:1;
  cursor:not-allowed;
}
.task-panel .location-trigger.is-fixed:disabled svg{color:var(--dispatch-control-disabled-text)}
.dispatch-location-fields{display:grid;grid-column:1/-1;grid-template-columns:repeat(2,minmax(0,1fr));align-items:start;gap:7px 10px;min-width:0}
.task-panel :is(.task-type-options,.location-options,.dispatch-calendar){
  color:var(--dispatch-control-text);
  background:var(--dispatch-popover-background);
  border-color:var(--dispatch-control-border);
}
.task-panel :is(.task-type-options button:hover,.task-type-options button[aria-selected=true],.location-options button:hover,.location-options button[aria-selected=true],.dispatch-calendar button:hover){
  color:var(--dispatch-popover-hover-text);
  background:var(--dispatch-popover-hover-background);
}
.task-panel .calendar-grid button[aria-pressed=true]{
  color:var(--dispatch-popover-hover-text);
  background:var(--dispatch-popover-hover-background);
}
.task-panel :is(input,textarea)::placeholder{color:var(--text-muted)}
.task-panel footer{background:transparent!important;border-color:var(--panel-border)}
.task-panel footer button:not(.create-button){color:var(--text-primary);background:transparent}
.task-panel footer .create-button{color:var(--dispatch-popover-hover-text)!important;background:var(--theme-primary)!important;box-shadow:none}
.task-panel footer .create-button:hover{background:var(--theme-primary-hover)!important;box-shadow:0 6px 16px color-mix(in srgb,var(--theme-primary) 30%,transparent)}
@media(prefers-reduced-motion:reduce){.task-panel footer button{transition:none}}
</style>

<style scoped>
.dispatch-time-entry{position:relative}
.dispatch-time-entry input{width:100%;box-sizing:border-box;padding-inline-end:32px}
.dispatch-time-entry button{position:absolute;inset-inline-end:4px;top:50%;transform:translateY(-50%);display:grid;place-items:center;width:25px;height:25px;padding:0;border:0;border-radius:5px;background:transparent;color:var(--dispatch-control-label);cursor:pointer}
.dispatch-time-options{position:fixed;z-index:1100;box-sizing:border-box;display:grid;grid-template-columns:minmax(0,1fr) 10px minmax(0,1fr);align-items:start;gap:4px;width:152px;padding:5px;overflow:auto;border:1px solid var(--dispatch-control-border);border-radius:9px;background:var(--dispatch-popover-background);color:var(--dispatch-control-text);box-shadow:0 10px 22px #34433825}
.dispatch-time-options > span{text-align:center;padding-top:6px}
.time-scroll-column{position:relative;display:grid;gap:2px;max-height:132px;overflow-y:auto;overscroll-behavior:contain;scrollbar-width:thin}
.time-scroll-column button{min-height:26px;padding:2px;border:0;border-radius:5px;background:transparent;color:inherit;font:inherit;font-size:13px;cursor:pointer}
.time-scroll-column button:hover{background:var(--dispatch-popover-hover-background)}
.time-scroll-column button[aria-selected=true]{color:var(--dispatch-popover-hover-text);background:var(--theme-primary)}
</style>
