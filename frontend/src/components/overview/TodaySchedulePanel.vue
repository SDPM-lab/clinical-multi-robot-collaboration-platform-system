<script setup>
import { computed, nextTick, ref } from 'vue'
import { demoSchedule } from '@/data/demoSchedule.js'
import { getRobotVisualTheme, semanticColors } from '@/config/robotVisualThemes.js'
import { Check } from '@lucide/vue'
import GlassPanel from './GlassPanel.vue'

const todayDate = '2026-08-31'
const selectedDate = ref(todayDate)
const dayButtons = ref([])
const weekDays = Object.freeze([
  { date: '2026-08-28', month: 8, day: '28', weekday: '星期五' },
  { date: '2026-08-29', month: 8, day: '29', weekday: '星期六' },
  { date: '2026-08-30', month: 8, day: '30', weekday: '星期日' },
  { date: '2026-08-31', month: 8, day: '31', weekday: '星期一' },
  { date: '2026-09-01', month: 9, day: '01', weekday: '星期二' },
  { date: '2026-09-02', month: 9, day: '02', weekday: '星期三' },
  { date: '2026-09-03', month: 9, day: '03', weekday: '星期四' },
])

const selectedDay = computed(() => (
  weekDays.find(({ date }) => date === selectedDate.value) || weekDays[3]
))
const selectedSchedule = computed(() => (
  demoSchedule.filter(({ date }) => date === selectedDate.value)
))
const dateHeading = computed(() => (
  `${selectedDay.value.month}月${Number(selectedDay.value.day)}日・${selectedDay.value.weekday}`
))
const scheduleHeading = computed(() => (
  selectedDate.value === todayDate ? '今日排程' : '當日排程'
))
const scheduleStyle = (item) => ({
  '--schedule-color': item.robotId ? getRobotVisualTheme(item.robotId).main : '#A8AAA5',
  '--success-color': semanticColors.success,
})

const selectDate = (date) => { selectedDate.value = date }
const selectAdjacentDate = async (index, offset) => {
  const nextIndex = (index + offset + weekDays.length) % weekDays.length
  selectDate(weekDays[nextIndex].date)
  await nextTick()
  dayButtons.value[nextIndex]?.focus()
}
const selectBoundaryDate = async (index) => {
  selectDate(weekDays[index].date)
  await nextTick()
  dayButtons.value[index]?.focus()
}
</script>

<template>
  <GlassPanel class="schedule-panel">
    <header class="schedule-header">
      <strong>{{ dateHeading }}</strong>
      <button type="button">查看全部</button>
    </header>
    <div class="schedule-week" aria-label="8月31日當週日期">
      <button
        v-for="(item, index) in weekDays"
        ref="dayButtons"
        :key="item.date"
        type="button"
        class="schedule-day"
        :class="{ 'schedule-day--active': selectedDate === item.date }"
        :aria-label="`${item.month}月${Number(item.day)}日 ${item.weekday}`"
        :aria-pressed="selectedDate === item.date"
        @click="selectDate(item.date)"
        @keydown.left.prevent="selectAdjacentDate(index, -1)"
        @keydown.right.prevent="selectAdjacentDate(index, 1)"
        @keydown.home.prevent="selectBoundaryDate(0)"
        @keydown.end.prevent="selectBoundaryDate(weekDays.length - 1)"
      >
        <strong>{{ item.day }}</strong>
        <i aria-hidden="true"></i>
      </button>
    </div>
    <h2>{{ scheduleHeading }}</h2>
    <ol v-if="selectedSchedule.length" class="schedule-list">
      <li v-for="item in selectedSchedule" :key="item.id" :data-status="item.status" :style="scheduleStyle(item)">
        <time>{{ item.time }}</time>
        <span class="schedule-title" :title="item.title">{{ item.title }}</span>
        <span class="schedule-assignee" :title="item.assignee">{{ item.assignee }}</span>
        <Check v-if="item.status === 'completed'" class="schedule-success" :size="13" aria-label="已成功" />
      </li>
    </ol>
    <p v-else class="schedule-empty">當日沒有排程</p>
  </GlassPanel>
</template>

<style scoped>
.schedule-panel { height: 292px; padding: 18px 20px; }
.schedule-panel :deep(.glass-panel__content) { padding-top: 0; }
.schedule-header { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.schedule-header strong { color: var(--text-primary); font-size: 15px; font-weight: 650; }
.schedule-header button { padding: 4px 0; color: var(--accent-wood); font-size: 12.5px; background: transparent; border: 0; cursor: pointer; }
.schedule-header button:hover, .schedule-header button:focus-visible { color: var(--accent-orange); }
.schedule-header button:focus-visible { outline: 2px solid var(--accent-beige); outline-offset: 3px; }
.schedule-week { display: grid; grid-template-columns: repeat(7, 1fr); gap: 3px; margin: 13px 0 12px; }
.schedule-day { display: grid; min-width: 0; padding: 3px 0; justify-items: center; gap: 5px; color: var(--text-muted); background: transparent; border: 0; border-radius: 9px; cursor: pointer; transition: color 160ms ease, background-color 160ms ease, transform 160ms ease; }
.schedule-day:hover { color: var(--accent-wood); background: var(--icon-button-hover); transform: translateY(-1px); }
.schedule-day:focus-visible { outline: 2px solid var(--accent-beige); outline-offset: 1px; }
.schedule-week strong { font-size: 13px; font-weight: 550; }
.schedule-week i { width: 5px; height: 5px; background: transparent; border-radius: 50%; }
.schedule-week .schedule-day--active { color: var(--text-primary); background: var(--icon-button-hover); }
.schedule-week .schedule-day--active i { background: var(--accent-orange); }
.schedule-panel h2 { margin: 0 0 7px; color: var(--text-primary); font-size: 14px; font-weight: 650; }
.schedule-list { display: grid; gap: 2px; margin: 0; padding: 0; list-style: none; }
.schedule-list li { position: relative; display: grid; grid-template-columns: 42px minmax(0, 1fr) minmax(66px, auto); align-items: center; min-height: 34px; gap: 8px; padding-left: 9px; color: var(--text-secondary); font-size: 12.5px; }
.schedule-list li::before { position: absolute; top: 7px; bottom: 7px; left: 0; width: 3px; background: var(--schedule-color); border-radius: 3px; content: ''; }
.schedule-success { color:var(--success-color); }
.schedule-list time { color: var(--text-primary); font-variant-numeric: tabular-nums; }
.schedule-title, .schedule-assignee { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.schedule-title { color: var(--text-primary); }
.schedule-assignee { text-align: right; }
.schedule-empty { display: grid; min-height: 104px; margin: 0; place-items: center; color: var(--text-muted); font-size: 13px; }
@media (prefers-reduced-motion: reduce) { .schedule-day { transition-duration: 0.01ms; } }
</style>
