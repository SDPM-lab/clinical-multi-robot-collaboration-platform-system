<script setup>
import { computed, reactive, watch } from 'vue'
import { Check, ChevronLeft, ChevronRight, Pencil, RotateCcw, X } from '@lucide/vue'
import { localeTag, t, translateLocation, translateTask } from '@/i18n/index.js'
import { getRobotVisualTheme } from '@/config/robotVisualThemes.js'
import { shiftIsoDate } from './taskTimeline.js'

const props = defineProps({ date: { type: String, required: true }, tasks: { type: Array, required: true }, robots: { type: Array, required: true }, editing: { type: Boolean, default: false } })
const emit = defineEmits(['update:date', 'edit', 'reschedule', 'request-delete'])
const dateValue = (date) => new Date(`${date}T12:00:00`)
const todayIsoDate = () => { const now = new Date(); return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}` }
const heading = computed(() => new Intl.DateTimeFormat(localeTag.value, { year: 'numeric', month: 'long', day: 'numeric' }).format(dateValue(props.date)))
const days = computed(() => Array.from({ length: 5 }, (_, index) => {
  const date = shiftIsoDate(props.date, index - 2)
  const value = dateValue(date)
  return { date, day: value.getDate(), weekday: new Intl.DateTimeFormat(localeTag.value, { weekday: 'short' }).format(value) }
}))
const draftTimes = reactive({})
watch(() => props.tasks.map((task) => `${task.id}:${task.startTime}`).join('|'), () => { for (const task of props.tasks) draftTimes[task.id] = task.startTime.slice(0, 5) }, { immediate: true })
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
const robotName = (id) => props.robots.find((robot) => robot.id === id)?.name || id || '未指派'
const taskColor = (id) => id ? getRobotVisualTheme(id).main : '#9da8a4'
const taskTitle = (task) => `${robotName(task.robotId)} · ${translateTask(task.title)} · ${translateLocation(task.origin)} → ${translateLocation(task.destination)} · ${task.startTime.slice(0, 5)}–${task.endTime.slice(0, 5)}`
const saveTime = (task) => { if (draftTimes[task.id] && draftTimes[task.id] !== task.startTime.slice(0, 5)) emit('reschedule', task.id, draftTimes[task.id]) }
</script>

<template>
  <section class="schedule-sidebar" aria-label="任務排程">
    <div class="schedule-date-navigation">
      <button type="button" aria-label="前一天" @click="emit('update:date', shiftIsoDate(date, -1))"><ChevronLeft :size="16" /></button>
      <strong>{{ heading }}</strong>
      <button type="button" aria-label="後一天" @click="emit('update:date', shiftIsoDate(date, 1))"><ChevronRight :size="16" /></button>
    </div>
    <div class="schedule-days" aria-label="選擇日期">
      <button v-for="day in days" :key="day.date" type="button" :class="{ 'is-selected': day.date === date }" :aria-pressed="day.date === date" @click="emit('update:date', day.date)"><span>{{ day.weekday }}</span><strong>{{ day.day }}</strong></button>
    </div>
    <div class="schedule-list-heading"><strong>當日任務</strong><div class="schedule-list-tools"><span>{{ sortedTasks.length }} 項任務</span><button class="schedule-today" type="button" :aria-label="t('dispatch.todaySchedule')" :title="t('dispatch.todaySchedule')" @click="emit('update:date', todayIsoDate())"><RotateCcw :size="15" /></button><button class="schedule-edit" type="button" :aria-label="editing ? t('dispatch.doneEditing') : t('dispatch.edit')" :title="editing ? t('dispatch.doneEditing') : t('dispatch.edit')" :aria-pressed="editing" @click="emit('edit')"><Check v-if="editing" :size="15" /><Pencil v-else :size="15" /></button></div></div>
    <div class="schedule-list">
      <p v-if="!sortedTasks.length" class="schedule-empty">目前沒有排定任務</p>
      <div v-for="slot in timeSlots" :key="slot.time" class="schedule-slot" :class="{ 'is-concurrent': slot.tasks.length > 1 }">
        <div class="schedule-time"><strong>{{ slot.time }}</strong><span>{{ slot.tasks.length === 1 ? slot.tasks[0].endTime.slice(0, 5) : t('dispatch.robotCount', { count: slot.tasks.length }) }}</span></div>
        <div class="schedule-slot-cards" :class="{ 'is-editing': editing }" :style="{ '--slot-columns': Math.min(slot.tasks.length, 3) }">
          <article v-for="task in slot.tasks" :key="task.id" class="schedule-item" :style="{ '--item-color': taskColor(task.robotId) }" :title="taskTitle(task)" :aria-label="taskTitle(task)">
            <button v-if="editing" class="schedule-delete" type="button" :aria-label="`${t('dispatch.deleteTask')} ${task.id}`" :title="t('dispatch.deleteTask')" @click="emit('request-delete', task)"><X :size="13" /></button>
            <div class="schedule-card-top"><span>{{ task.id }} · {{ task.robotId || robotName(task.robotId) }}</span></div>
            <h3>{{ translateTask(task.title) }}</h3>
            <p>{{ translateLocation(task.origin) }} → {{ translateLocation(task.destination) }}</p>
            <div v-if="editing" class="schedule-inline-edit"><label><span>{{ t('dispatch.startTime') }}</span><input v-model="draftTimes[task.id]" type="time" :aria-label="`${t('dispatch.startTime')} ${task.id}`"></label><button type="button" :aria-label="`${t('dispatch.saveTime')} ${task.id}`" :title="t('dispatch.saveTime')" :disabled="!draftTimes[task.id] || draftTimes[task.id] === task.startTime.slice(0, 5)" @click="saveTime(task)"><Check :size="14" /></button></div>
          </article>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.schedule-sidebar{display:flex;flex-direction:column;width:100%;height:100%;min-width:0;min-height:0;color:var(--text-primary)}
.schedule-header{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:11px 14px 8px}.schedule-header h2{margin:0;font-size:15px;font-weight:650}.schedule-header-actions{display:flex;align-items:center;gap:5px}.schedule-header-actions button{display:grid;place-items:center;width:29px;height:29px;border-radius:8px;cursor:pointer}.schedule-today{color:var(--text-secondary);background:var(--surface-glass);border:1px solid var(--panel-border)}.schedule-today:hover{background:var(--icon-button-hover)}.schedule-edit{color:#dc784b;background:#fff5ef;border:1px solid #f7d9ca}.schedule-edit:hover,.schedule-edit[aria-pressed=true]{background:#ffe9dc}
.schedule-date-navigation{display:flex;align-items:center;justify-content:space-between;margin:0 14px;padding:4px 0;border-top:1px solid var(--panel-border)}.schedule-date-navigation strong{font-size:12px;font-weight:600}.schedule-date-navigation button{display:grid;width:27px;height:27px;place-items:center;color:var(--text-secondary);background:transparent;border:0;border-radius:7px;cursor:pointer}.schedule-date-navigation button:hover{background:var(--icon-button-hover)}
.schedule-days{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:3px;padding:0 12px 6px}.schedule-days button{display:grid;gap:0;justify-items:center;min-height:39px;padding:4px 0;color:var(--text-muted);background:transparent;border:0;border-radius:7px;cursor:pointer}.schedule-days button span{font-size:9px}.schedule-days button strong{font-size:12px;font-weight:600;color:var(--text-primary)}.schedule-days button.is-selected{color:#fff;background:#f49466;box-shadow:0 4px 10px #f4946630}.schedule-days button.is-selected strong{color:#fff}
.schedule-list-heading{display:flex;align-items:center;justify-content:space-between;padding:7px 14px;border-top:1px solid var(--panel-border)}.schedule-list-heading strong{font-size:12px;font-weight:650}.schedule-list-heading span{font-size:10px;color:var(--text-muted)}
.schedule-list{flex:1;min-height:0;overflow:auto;padding:0 12px 9px;scrollbar-width:thin;overscroll-behavior:contain}.schedule-empty{padding:30px 10px;text-align:center;color:var(--text-muted);font-size:12px}
.schedule-slot{display:grid;grid-template-columns:42px minmax(0,1fr);gap:8px;align-items:start;margin-bottom:6px}.schedule-time{display:grid;gap:2px;padding-top:5px;text-align:right;font-variant-numeric:tabular-nums}.schedule-time strong{font-size:11px;font-weight:650}.schedule-time span{font-size:9px;color:var(--text-muted)}
.schedule-slot-cards{display:grid;grid-template-columns:repeat(var(--slot-columns),minmax(0,1fr));gap:5px;min-width:0}.schedule-item{box-sizing:border-box;min-width:0;min-height:51px;padding:6px 9px;background:color-mix(in srgb,var(--panel-bg-strong) 89%,var(--item-color));border:1px solid color-mix(in srgb,var(--panel-border) 75%,var(--item-color));border-left:3px solid var(--item-color);border-radius:8px;box-shadow:0 3px 10px #36413b0a}.schedule-card-top{overflow:hidden;color:var(--text-muted);font-size:9px;text-overflow:ellipsis;white-space:nowrap}.schedule-item h3{overflow:hidden;margin:2px 0;color:var(--text-primary);font-size:11px;font-weight:650;line-height:1.3;text-overflow:ellipsis;white-space:nowrap}.schedule-item p{overflow:hidden;margin:0;color:var(--text-secondary);font-size:9px;text-overflow:ellipsis;white-space:nowrap}
.is-concurrent .schedule-item{min-height:49px;padding:5px 6px}.is-concurrent .schedule-item h3{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;white-space:normal;line-height:1.2}.is-concurrent .schedule-item p{display:none}
.schedule-item{position:relative}.schedule-delete{position:absolute;top:5px;right:5px;display:grid;place-items:center;width:21px;height:21px;padding:0;color:#a26360;background:color-mix(in srgb,var(--panel-bg-strong) 82%,transparent);border:1px solid var(--panel-border);border-radius:6px;cursor:pointer}.schedule-delete:hover{color:#a93c32;background:#fff1ee}.schedule-slot-cards.is-editing{grid-template-columns:1fr}.is-editing .schedule-item{padding-right:32px}.is-editing .schedule-item p{display:block}.schedule-inline-edit{display:flex;align-items:end;gap:6px;margin-top:7px}.schedule-inline-edit label{display:grid;gap:2px;min-width:0;color:var(--text-secondary);font-size:9px}.schedule-inline-edit input{box-sizing:border-box;width:118px;max-width:100%;height:27px;padding:2px 5px;color:var(--text-primary);background:var(--panel-bg-strong);border:1px solid var(--panel-border);border-radius:6px;font:inherit;font-size:10px}.schedule-inline-edit button{display:grid;place-items:center;width:27px;height:27px;padding:0;color:#4b856b;background:#ecf8f1;border:1px solid #bbdfca;border-radius:6px;cursor:pointer}.schedule-inline-edit button:disabled{opacity:.45;cursor:default}
.schedule-date-navigation{border-top:0;padding-top:10px}.schedule-date-navigation strong{font-size:14px}.schedule-days button span{font-size:10.5px}.schedule-days button strong{font-size:13px}.schedule-list-heading{min-height:40px}.schedule-list-heading strong{font-size:14px}.schedule-list-tools{display:flex;align-items:center;gap:5px}.schedule-list-tools span{margin-right:4px;color:var(--text-muted);font-size:11px}.schedule-list-tools button{display:grid;place-items:center;width:26px;height:26px;padding:0;border-radius:7px;cursor:pointer}.schedule-time strong{font-size:12px}.schedule-time span{font-size:10px}.schedule-card-top{font-size:10px}.schedule-item h3{font-size:13px}.schedule-item p{font-size:10px}
</style>
