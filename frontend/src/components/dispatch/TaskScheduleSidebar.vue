<script setup>
import { computed, nextTick, onMounted, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { Check, Clock3, ChevronLeft, ChevronRight, Pencil, RotateCcw, X } from '@lucide/vue'
import { localeTag, t, translateLocation, translateTask } from '@/i18n/index.js'
import { taskPriorityColor } from '@/config/taskPriorityColors.js'
import { robotDisplayCode } from '@/config/robotDisplayCode.js'
import { shiftIsoDate } from './taskTimeline.js'

const props = defineProps({ date: { type: String, required: true }, tasks: { type: Array, required: true }, robots: { type: Array, required: true }, editing: { type: Boolean, default: false } })
const emit = defineEmits(['update:date', 'edit', 'save-edits', 'request-delete'])
const dateValue = (date) => new Date(`${date}T12:00:00`)
const todayIsoDate = () => { const now = new Date(); return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}` }
const heading = computed(() => new Intl.DateTimeFormat(localeTag.value, { year: 'numeric', month: 'long', day: 'numeric' }).format(dateValue(props.date)))
const days = computed(() => Array.from({ length: 5 }, (_, index) => {
  const date = shiftIsoDate(props.date, index - 2)
  const value = dateValue(date)
  return { date, day: value.getDate(), weekday: new Intl.DateTimeFormat(localeTag.value, { weekday: 'short' }).format(value) }
}))
const openTimePicker = ref(null)
const sidebarRoot = ref(null)
const closeTimePickerOutside = event => {
  const picker = sidebarRoot.value?.querySelector('.schedule-time-options')?.closest('.schedule-time-picker')
  if (picker && !picker.contains(event.target)) openTimePicker.value = null
}
onMounted(() => document.addEventListener('pointerdown', closeTimePickerOutside))
onBeforeUnmount(() => document.removeEventListener('pointerdown', closeTimePickerOutside))
const hours = Array.from({ length: 24 }, (_, i) => String(i).padStart(2, '0'))
const minutes = Array.from({ length: 60 }, (_, i) => String(i).padStart(2, '0'))
const validTime = (value) => /^([01]\d|2[0-3]):[0-5]\d$/.test(value || '')
const pickerAbove = ref(false)
const openPicker = async (id, event) => {
  const trigger = event.currentTarget
  pickerAbove.value = trigger.getBoundingClientRect().bottom + 185 >
    (trigger.closest('.schedule-list')?.getBoundingClientRect().bottom || window.innerHeight)
  openTimePicker.value = id
  await nextTick()
  const picker = trigger.closest('.schedule-time-picker')
  picker?.querySelectorAll('[aria-selected="true"]').forEach(option => {
    const column = option.parentElement
    column.scrollTop = option.offsetTop - column.offsetTop - 54
  })
}
const chooseTimePart = (id, part, value) => {
  const parts = validTime(draftTimes[id]) ? draftTimes[id].split(':') : ['00', '00']
  parts[part] = value
  draftTimes[id] = parts.join(':')
}
watch(() => props.editing, () => {
  openTimePicker.value = null
  for (const task of props.tasks) {
    draftTimes[task.id] = task.startTime.slice(0,5)
  }
})
const draftTimes = reactive({})
watch(() => props.tasks.map((task) => `${task.id}:${task.startTime}`).join('|'), () => { for (const task of props.tasks) draftTimes[task.id] = task.startTime.slice(0, 5) }, { immediate: true })
const canEditTask = task => ['pending', 'assigned'].includes(String(task.status).toLowerCase()) && !task.startedAt
const canDeleteTask = task => String(task.status).toLowerCase() === 'pending'
const canSaveEdits = task => canEditTask(task) && validTime(draftTimes[task.id]) &&
  draftTimes[task.id] !== task.startTime.slice(0, 5) &&
  new Date(`${props.date}T${draftTimes[task.id]}:00`) > new Date()
const saveEdits = task => {
  if (!canSaveEdits(task)) return
  emit('save-edits', task.id, draftTimes[task.id])
  openTimePicker.value = null
}
const sortedTasks = computed(() => [...props.tasks].sort((a, b) => a.startTime.localeCompare(b.startTime) || (a.robotId || '').localeCompare(b.robotId || '')))
const timeSlots = computed(() => {
  const slots = []
  for (const task of sortedTasks.value) {
    const time = task.startTime.slice(0, 5)
    let slot = slots.at(-1)
    if (!slot || slot.time !== time) { slot = { time, tasks: [] }; slots.push(slot) }
    slot.tasks.push(task)
  }
  return slots
})
const assignedRobotId = task => task.assignedRobot || task.robotId || ''
const robotName = (id) => id ? robotDisplayCode(id) : t('dispatch.unassigned')
const taskTitle = (task) => `${robotName(task.robotId)} · ${translateTask(task.title)} · ${translateLocation(task.source)} → ${translateLocation(task.destination)} · ${task.startTime.slice(0, 5)}–${task.endTime.slice(0, 5)}`
</script>

<template>
  <section ref="sidebarRoot" class="schedule-sidebar" :aria-label="t('dispatch.scheduleTab')">
    <div class="schedule-date-navigation">
      <button type="button" :aria-label="t('dispatch.previousDay')" @click="emit('update:date', shiftIsoDate(date, -1))"><ChevronLeft :size="16" /></button>
      <strong>{{ heading }}</strong>
      <div class="schedule-date-actions">
        <button type="button" :aria-label="t('dispatch.nextDay')" @click="emit('update:date', shiftIsoDate(date, 1))"><ChevronRight :size="16" /></button>
      </div>
    </div>
    <div class="schedule-days" :aria-label="t('dispatch.chooseDate')">
      <button v-for="day in days" :key="day.date" type="button" :class="{ 'is-selected': day.date === date }" :aria-pressed="day.date === date" @click="emit('update:date', day.date)"><span>{{ day.weekday }}</span><strong>{{ day.day }}</strong></button>
    </div>
    <div class="schedule-list-heading"><strong>{{ t('dispatch.dailyTasks') }}</strong><div class="schedule-list-tools"><span>{{ t('dispatch.taskCount', { count: sortedTasks.length }) }}</span><button class="schedule-today" type="button" :aria-label="t('dispatch.todaySchedule')" :title="t('dispatch.todaySchedule')" @click="emit('update:date', todayIsoDate())"><RotateCcw :size="15" /></button><button class="schedule-edit" type="button" :aria-label="editing ? t('dispatch.doneEditing') : t('dispatch.edit')" :title="editing ? t('dispatch.doneEditing') : t('dispatch.edit')" :aria-pressed="editing" @click="emit('edit')"><Check v-if="editing" :size="15" /><Pencil v-else :size="15" /></button></div></div>
    <div class="schedule-list">
      <p v-if="!sortedTasks.length" class="schedule-empty">{{ t('dispatch.emptySchedule') }}</p>
      <div v-for="slot in timeSlots" :key="slot.time" class="schedule-slot" :class="{ 'is-concurrent': slot.tasks.length > 1 }">
        <div class="schedule-time"><strong>{{ slot.time }}</strong><span>{{ slot.tasks.length === 1 ? slot.tasks[0].endTime.slice(0, 5) : t('dispatch.robotCount', { count: slot.tasks.length }) }}</span></div>
        <div class="schedule-slot-cards" :class="{ 'is-editing': editing }" :style="{ '--slot-columns': Math.min(slot.tasks.length, 3) }">
          <article v-for="task in slot.tasks" :key="task.id" class="schedule-item" :data-priority="task.priority" :style="{ '--item-color': taskPriorityColor(task.priority) }" :title="taskTitle(task)" :aria-label="taskTitle(task)">
            <button v-if="editing && canDeleteTask(task)" class="schedule-delete" type="button" :aria-label="`${t('dispatch.deleteTask')} ${task.taskCode || task.id}`" :title="t('dispatch.deleteTask')" @click="emit('request-delete', task)"><X :size="13" /></button>
            <div class="schedule-card-top"><span>{{ task.taskCode || task.id }} · {{ robotName(assignedRobotId(task)) }}</span></div>
            <span v-if="['assigned','running'].includes(String(task.status).toLowerCase())" class="assignment-status" :data-status="String(task.status).toLowerCase()">{{ t(String(task.status).toLowerCase() === 'assigned' ? 'dispatchUx.assignedWaiting' : 'status.running') }}</span>
            <h3>{{ translateTask(task.title) }}</h3>
            <p>{{ translateLocation(task.source) }} → {{ translateLocation(task.destination) }}</p>
            <div v-if="editing && canEditTask(task)" class="schedule-inline-edit"><label><span>{{ t('dispatch.startTime') }}</span><div class="schedule-time-picker" @keydown.esc.stop="openTimePicker=null" @focusout="!$event.currentTarget.contains($event.relatedTarget) && (openTimePicker=null)"><div class="schedule-time-entry"><input v-model="draftTimes[task.id]" type="text" inputmode="numeric" placeholder="HH:mm" pattern="([01][0-9]|2[0-3]):[0-5][0-9]" :aria-label="`${t('dispatch.startTime')} ${task.taskCode || task.id}`" @click="openPicker(task.id,$event)" @keydown.down.prevent="openPicker(task.id,$event)"><button class="schedule-time-toggle" type="button" :aria-label="`${t('dispatchForm.chooseTime')} ${task.taskCode || task.id}`" :aria-expanded="openTimePicker===task.id" @click="openTimePicker===task.id ? openTimePicker=null : openPicker(task.id,$event)"><Clock3 :size="14" /></button></div><div v-if="openTimePicker===task.id" class="schedule-time-options" :class="{ 'opens-above': pickerAbove }"><div class="schedule-time-column" role="listbox" :aria-label="`${t('dispatch.startTime')} ${task.taskCode || task.id} HH`"><button v-for="hour in hours" :key="hour" type="button" role="option" :aria-selected="draftTimes[task.id]?.slice(0,2)===hour" @click="chooseTimePart(task.id,0,hour)">{{ hour }}</button></div><span class="time-colon" aria-hidden="true">:</span><div class="schedule-time-column" role="listbox" :aria-label="`${t('dispatch.startTime')} ${task.taskCode || task.id} mm`"><button v-for="minute in minutes" :key="minute" type="button" role="option" :aria-selected="draftTimes[task.id]?.slice(3,5)===minute" @click="chooseTimePart(task.id,1,minute)">{{ minute }}</button></div></div></div></label></div>
            <p v-if="editing" class="schedule-edit-hint">{{ t(canEditTask(task) ? 'dispatchUx.rescheduleHint' : 'dispatchUx.taskLocked') }}</p>
            <div v-if="editing && canEditTask(task)" class="schedule-edit-actions"><button class="save-task-edits" type="button" :aria-label="`${t('dispatchUx.requeue')} ${task.taskCode || task.id}`" :disabled="!canSaveEdits(task)" @click="saveEdits(task)"><Check :size="14" /><span>{{ t('dispatchUx.requeue') }}</span></button></div>
          </article>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.schedule-sidebar{display:flex;flex-direction:column;width:100%;height:100%;min-width:0;min-height:0;color:var(--text-primary)}
.schedule-header{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:11px 14px 8px}.schedule-header h2{margin:0;font-size:15px;font-weight:650}.schedule-header-actions{display:flex;align-items:center;gap:5px}.schedule-header-actions button{display:grid;place-items:center;width:29px;height:29px;border-radius:8px;cursor:pointer}.schedule-today{color:var(--text-secondary);background:var(--surface-glass);border:1px solid var(--panel-border)}.schedule-today:hover{background:var(--icon-button-hover)}.schedule-edit{color:#dc784b;background:#fff5ef;border:1px solid #f7d9ca}.schedule-edit:hover,.schedule-edit[aria-pressed=true]{background:#ffe9dc}
.schedule-date-navigation{display:grid;grid-template-columns:58px minmax(0,1fr) 58px;align-items:center;margin:0 14px;padding:4px 0;border-top:1px solid var(--panel-border)}.schedule-date-navigation strong{text-align:center;font-size:12px;font-weight:600}.schedule-date-actions{display:flex;justify-content:flex-end;gap:2px}.schedule-date-navigation button{display:grid;width:27px;height:27px;place-items:center;color:var(--text-secondary);background:transparent;border:0;border-radius:7px;cursor:pointer}.schedule-date-navigation button:hover{background:var(--icon-button-hover)}.schedule-date-navigation .schedule-today{color:#dc784b;background:var(--surface-glass);border:1px solid var(--panel-border)}.schedule-date-navigation .schedule-today:hover{background:var(--icon-button-hover)}
.schedule-days{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:3px;padding:0 12px 6px}.schedule-days button{display:grid;gap:0;justify-items:center;min-height:39px;padding:4px 0;color:var(--text-muted);background:transparent;border:0;border-radius:7px;cursor:pointer}.schedule-days button span{font-size:9px}.schedule-days button strong{font-size:12px;font-weight:600;color:var(--text-primary)}.schedule-days button.is-selected{color:#fff;background:#f49466;box-shadow:0 4px 10px #f4946630}.schedule-days button.is-selected strong{color:#fff}
.schedule-list-heading{display:flex;align-items:center;justify-content:space-between;padding:7px 14px;border-top:1px solid var(--panel-border)}.schedule-list-heading strong{font-size:12px;font-weight:650}.schedule-list-heading span{font-size:10px;color:var(--text-muted)}
.schedule-list{flex:1;min-height:0;overflow:auto;padding:0 12px 9px;scrollbar-width:thin;overscroll-behavior:contain}.schedule-empty{padding:30px 10px;text-align:center;color:var(--text-muted);font-size:12px}
.schedule-slot{display:grid;grid-template-columns:42px minmax(0,1fr);gap:8px;align-items:start;margin-bottom:6px}.schedule-time{display:grid;gap:2px;padding-top:5px;text-align:right;font-variant-numeric:tabular-nums}.schedule-time strong{font-size:11px;font-weight:650}.schedule-time span{font-size:9px;color:var(--text-muted)}
.schedule-slot-cards{display:grid;grid-template-columns:repeat(var(--slot-columns),minmax(0,1fr));gap:5px;min-width:0}.schedule-item{box-sizing:border-box;min-width:0;min-height:51px;padding:6px 9px;background:color-mix(in srgb,var(--panel-bg-strong) 89%,var(--item-color));border:1px solid color-mix(in srgb,var(--panel-border) 75%,var(--item-color));border-left:3px solid var(--item-color);border-radius:8px;box-shadow:0 3px 10px #36413b0a}.schedule-card-top{overflow:hidden;color:var(--text-muted);font-size:9px;text-overflow:ellipsis;white-space:nowrap}.schedule-item h3{overflow:hidden;margin:2px 0;color:var(--text-primary);font-size:11px;font-weight:650;line-height:1.3;text-overflow:ellipsis;white-space:nowrap}.schedule-item p{overflow:hidden;margin:0;color:var(--text-secondary);font-size:9px;text-overflow:ellipsis;white-space:nowrap}
.is-concurrent .schedule-item{min-height:49px;padding:5px 6px}.is-concurrent .schedule-item h3{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;white-space:normal;line-height:1.2}.is-concurrent .schedule-item p{display:none}
.schedule-item{position:relative}.schedule-delete{position:absolute;top:5px;right:5px;display:grid;place-items:center;width:21px;height:21px;padding:0;color:#a26360;background:color-mix(in srgb,var(--panel-bg-strong) 82%,transparent);border:1px solid var(--panel-border);border-radius:6px;cursor:pointer}.schedule-delete:hover{color:#a93c32;background:#fff1ee}.schedule-slot-cards.is-editing{grid-template-columns:1fr}.is-editing .schedule-item{padding-right:32px}.is-editing .schedule-item p{display:block}.schedule-inline-edit{display:flex;align-items:end;gap:6px;margin-top:7px}.schedule-inline-edit label{display:grid;gap:2px;min-width:0;color:var(--text-secondary);font-size:9px}.schedule-inline-edit input{box-sizing:border-box;width:118px;max-width:100%;height:27px;padding:2px 5px;color:var(--text-primary);background:var(--panel-bg-strong);border:1px solid var(--panel-border);border-radius:6px;font:inherit;font-size:10px}.schedule-inline-edit button{display:grid;place-items:center;width:27px;height:27px;padding:0;color:#4b856b;background:#ecf8f1;border:1px solid #bbdfca;border-radius:6px;cursor:pointer}.schedule-inline-edit button:disabled{opacity:.45;cursor:default}
.schedule-date-navigation{border-top:0;padding-top:10px}.schedule-date-navigation strong{font-size:14px}.schedule-days button span{font-size:10.5px}.schedule-days button strong{font-size:13px}.schedule-list-heading{min-height:40px}.schedule-list-heading strong{font-size:14px}.schedule-list-tools{display:flex;align-items:center;gap:5px}.schedule-list-tools span{margin-right:4px;color:var(--text-muted);font-size:11px}.schedule-list-tools button{display:grid;place-items:center;width:26px;height:26px;padding:0;border-radius:7px;cursor:pointer}.schedule-time strong{font-size:12px}.schedule-time span{font-size:10px}.schedule-card-top{font-size:10px}.schedule-item h3{font-size:13px}.schedule-item p{font-size:10px}

.schedule-list-tools .schedule-today,.schedule-list-tools .schedule-edit{color:var(--text-secondary);background:#fff;border:1px solid var(--panel-border);transition:background .15s,color .15s}
.schedule-list-tools .schedule-today:hover,.schedule-list-tools .schedule-edit:hover{color:#b85525;background:#ffe9dc;border-color:#fb9966}
.schedule-list-tools button:focus-visible,.schedule-time-picker button:focus-visible{outline:2px solid #fb9966;outline-offset:2px}
.schedule-time-picker{width:142px;max-width:100%}.schedule-time-entry{display:flex;align-items:center;background:var(--panel-bg-strong);border:1px solid var(--panel-border);border-radius:6px}.schedule-time-entry:focus-within{border-color:#fb9966;box-shadow:0 0 0 2px #fb996633}.schedule-time-entry input{width:100%;min-width:0;border:0;background:transparent;outline:none}.schedule-inline-edit .schedule-time-toggle{flex:none;width:25px;height:25px;color:var(--text-secondary);background:transparent;border:0}.schedule-time-options{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:3px;max-height:150px;margin-top:4px;padding:5px;overflow:auto;background:var(--panel-bg-strong);border:0;border-radius:7px;scrollbar-width:thin;scrollbar-color:#fb9966 transparent}.schedule-inline-edit .schedule-time-options button{width:100%;height:27px;color:var(--text-primary);background:transparent;border:0;font:inherit;font-size:11px}.schedule-inline-edit .schedule-time-options button:hover,.schedule-inline-edit .schedule-time-options button[aria-selected=true]{color:#813c1c;background:#ffe4d4}

.schedule-time-picker{position:relative}
.schedule-time-options{position:absolute;z-index:40;top:100%;left:0;box-sizing:border-box;width:142px;grid-template-columns:1fr 10px 1fr;align-items:start;max-height:none;overflow:hidden;box-shadow:0 8px 24px #70361126;background:var(--panel-bg-strong,#fff)}
.schedule-time-options.opens-above{top:auto;bottom:100%;margin-top:0;margin-bottom:4px}
.schedule-time-column{position:relative;display:grid;gap:3px;max-height:150px;overflow-y:auto;overscroll-behavior:contain;scrollbar-width:thin;scrollbar-color:#fb9966 transparent}
.time-colon{padding-top:6px;text-align:center;color:var(--text-secondary);font-weight:600}
</style>

<style scoped>
.schedule-edit-hint{margin-top:8px!important;white-space:normal!important;font-size:10px!important;line-height:1.6}
.save-task-edits{color:#4b856b;background:#ecf8f1;border:1px solid #bbdfca;border-radius:6px;cursor:pointer}.save-task-edits:disabled{opacity:.45;cursor:default}
</style>

<style scoped>
.schedule-edit-actions{display:flex;justify-content:flex-end;margin-top:10px;padding-top:8px;border-top:1px solid var(--panel-border)}.schedule-edit-actions .save-task-edits{display:flex;align-items:center;justify-content:center;gap:5px;width:auto;min-height:30px;padding:0 10px;font:inherit;font-size:11px}.schedule-edit-actions .save-task-edits:not(:disabled):hover{color:#285d40;background:#d8efdf}.schedule-edit-actions .save-task-edits:focus-visible{outline:2px solid #fb9966;outline-offset:2px}
</style>

<style scoped>
.assignment-status{display:inline-flex;align-items:center;gap:4px;margin-top:4px;padding:3px 6px;border-radius:5px;color:#35627e;background:#e4f0f9;font-size:10px;font-weight:600;line-height:1.4}
.assignment-status[data-status=running]{color:#8b522c;background:#fff0de}
:global([data-theme='dark']) .assignment-status{color:#bbdff5;background:#304857}
:global([data-theme='dark']) .assignment-status[data-status=running]{color:#f5d2a6;background:#58452e}
</style>
