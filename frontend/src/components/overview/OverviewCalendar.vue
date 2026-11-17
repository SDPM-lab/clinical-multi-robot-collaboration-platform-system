<script setup>
import { computed, ref, watch } from 'vue'
import { ChevronLeft, ChevronRight } from '@lucide/vue'
import { locale, t, translateLocation, translateTask } from '@/i18n/index.js'

const props = defineProps({
  modelValue: { type: String, required: true },
  dates: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:modelValue','view-all'])
const visibleCount = 7
const windowStart = ref(0)
const selected = computed(() => props.dates.find((date) => date.key === props.modelValue) || props.dates[0])
const selectedLabel = computed(() => selected.value ? new Intl.DateTimeFormat(locale.value === 'en' ? 'en-US' : 'zh-TW', {month:'short',day:'numeric',weekday:'long'}).format(new Date(`${selected.value.key}T12:00:00`)) : '')
const formatDateLabel = (key) => new Intl.DateTimeFormat(locale.value === 'en' ? 'en-US' : 'zh-TW', {month:'long',day:'numeric',weekday:'long'}).format(new Date(`${key}T12:00:00`))
const visibleDates = computed(() => props.dates.slice(windowStart.value, windowStart.value + visibleCount))
const maxStart = computed(() => Math.max(0, props.dates.length - visibleCount))
const shiftDates = (amount) => { windowStart.value = Math.max(0, Math.min(maxStart.value, windowStart.value + amount)) }

watch([() => props.modelValue, () => props.dates], ([key]) => {
  const index = props.dates.findIndex((date) => date.key === key)
  if (index >= 0) windowStart.value = Math.max(0, Math.min(maxStart.value, index - 3))
}, { immediate: true })
</script>

<template>
  <section class="overview-calendar overview-tool-panel dashboard-panel-enter" :aria-label="t('dashboard.todaySchedule')">
    <header>
      <div class="calendar-heading"><h2>當日排程</h2><strong>{{ selectedLabel }}</strong></div>
      <button type="button" @click="emit('view-all', 'schedule')">查看全部</button>
    </header>
    <div class="date-navigator">
      <button type="button" class="date-arrow" :aria-label="t('common.previousDate')" :disabled="windowStart === 0" @click="shiftDates(-1)"><ChevronLeft :size="13" /></button>
      <nav :aria-label="t('common.scheduleDateNavigation')">
        <button v-for="date in visibleDates" :key="date.key" type="button" :class="{ 'is-selected': date.key === modelValue, 'is-today': date.today }" :aria-label="formatDateLabel(date.key)" :aria-pressed="date.key === modelValue" @click="emit('update:modelValue', date.key)"><span>{{ String(date.day).padStart(2, '0') }}</span><i :class="{ 'has-tasks': date.items?.length }"></i></button>
      </nav>
      <button type="button" class="date-arrow" :aria-label="t('common.nextDate')" :disabled="windowStart >= maxStart" @click="shiftDates(1)"><ChevronRight :size="13" /></button>
    </div>
    <Transition name="schedule-fade" mode="out-in">
      <div v-if="!selected?.items?.length" :key="`${modelValue}-empty`" class="schedule-empty">本日無排程</div>
      <ol v-else :key="modelValue" class="schedule-list" tabindex="0" :aria-label="t('dashboard.todayTaskList')">
        <li v-for="(item, index) in selected?.items" :key="item.id" :class="`is-${item.state}`" :style="{ '--schedule-index': Math.min(index, 4) }" :title="item.route">
          <i></i><time>{{ item.time }}</time><div class="schedule-task"><strong>{{ translateTask(item.title) }}</strong><small>{{ translateLocation(item.source) }} → {{ translateLocation(item.destination) }}</small></div><span>{{ item.assignee || t(`dashboard.${item.assignmentState || 'pending'}`) }}</span>
        </li>
      </ol>
    </Transition>
  </section>
</template>

<style scoped>
.schedule-task{display:grid;min-width:0;gap:2px}.schedule-task strong,.schedule-task small{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.schedule-task small{color:var(--text-secondary);font-size:10px}
.schedule-list{grid-auto-rows:minmax(58px,max-content);align-content:start}.schedule-list li{min-height:58px}
.overview-calendar{--panel-delay:280ms;box-sizing:border-box;display:flex;width:100%;height:100%;min-height:0;flex-direction:column;padding:20px;color:var(--text-primary)}header{flex-shrink:0;display:flex;align-items:center;justify-content:space-between;gap:12px}header strong{color:var(--text-primary);font-size:var(--info-title-size);font-weight:var(--info-title-weight);letter-spacing:var(--info-title-spacing)}header>button{padding:4px 0;color:var(--overview-accent-text);font-size:12px;background:transparent;border:0;cursor:pointer}.date-navigator{flex-shrink:0;display:grid;grid-template-columns:24px minmax(0,1fr) 24px;align-items:center;gap:5px;margin:13px 0 10px;padding-bottom:13px;border-bottom:1px solid var(--overview-border)}nav{display:grid;grid-template-columns:repeat(7,1fr);gap:3px}.date-arrow{display:grid;width:24px;height:30px;place-items:center;padding:0;color:var(--text-secondary);background:transparent;border:0;border-radius:var(--radius-control);cursor:pointer}.date-arrow:hover:not(:disabled){color:var(--overview-accent-text);transform:scale(1.12)}.date-arrow:focus-visible{outline:1px solid var(--overview-accent);outline-offset:2px}.date-arrow:disabled{opacity:.28;cursor:default}nav button{display:grid;height:36px;grid-template-rows:22px 4px;place-items:center;padding:4px 0 2px;color:var(--text-secondary);background:transparent;border:0;border-radius:var(--radius-control);cursor:pointer;transition:color 180ms ease,background-color 180ms ease}nav button span{font-size:12px;font-variant-numeric:tabular-nums}nav button i{width:4px;height:4px;background:transparent;border-radius:50%}nav button i.has-tasks{background:var(--neutral-slate)}nav button.is-today i,nav button.is-selected i{background:var(--overview-accent-text)}nav button:hover{color:var(--overview-accent-text)}nav button.is-selected{color:var(--overview-accent-text);background:var(--overview-accent-soft)}ol{display:grid;min-height:0;flex:1;grid-auto-rows:minmax(52px,1fr);overflow-y:auto;overflow-x:hidden;overscroll-behavior:contain;scrollbar-gutter:stable;scrollbar-width:thin;scrollbar-color:rgba(var(--overview-accent-rgb),.34) var(--overview-accent-soft);margin:0;padding:0 20px 0 0;list-style:none}li{display:grid;grid-template-columns:40px 5px minmax(0,1fr) 58px;align-items:center;gap:7px;min-width:0;opacity:0;animation:schedule-enter 360ms cubic-bezier(.22,1,.36,1) calc(450ms + var(--schedule-index)*150ms) forwards}li time,li span{color:var(--text-secondary);font-size:12px;font-variant-numeric:tabular-nums;white-space:nowrap}li>span{text-align:right}li strong{min-width:0;overflow:hidden;color:var(--text-primary);font-size:12.5px;font-weight:550;text-overflow:ellipsis;white-space:nowrap;word-break:keep-all}li>i{width:5px;height:5px;background:var(--overview-yellow);border-radius:50%}li.is-active>i{background:var(--overview-accent-text)}li.is-completed>i{background:var(--overview-neutral)}.schedule-empty{display:grid;min-height:0;flex:1;place-items:center;color:var(--text-secondary);font-size:12px}.schedule-fade-enter-active,.schedule-fade-leave-active{transition:opacity 150ms ease}.schedule-fade-enter-from,.schedule-fade-leave-to{opacity:0}
.schedule-list li{grid-template-columns:5px 40px minmax(0,1fr) 58px}
@keyframes schedule-enter{from{opacity:0;transform:translateX(6px)}to{opacity:1;transform:none}}
@media(prefers-reduced-motion:reduce){li{opacity:1;animation:none}.schedule-fade-enter-active,.schedule-fade-leave-active{transition:none}}
.calendar-heading{display:grid;gap:5px}.calendar-heading h2{margin:0;font-size:var(--font-panel-title);font-weight:var(--info-title-weight);letter-spacing:var(--info-title-spacing)}.date-navigator{animation:dashboard-fade 350ms ease 320ms both}nav button.is-selected{animation:dashboard-fade 420ms ease both}li time{font-size:11.5px}li>i{animation:dashboard-fade 200ms ease calc(720ms + var(--schedule-index)*150ms) both}
.schedule-list::-webkit-scrollbar{width:6px}.schedule-list::-webkit-scrollbar-track{background:var(--overview-accent-soft);border-radius:4px}.schedule-list::-webkit-scrollbar-thumb{background:rgba(var(--overview-accent-rgb),.34);border:1px solid rgba(255,255,255,.5);border-radius:4px}.schedule-list::-webkit-scrollbar-thumb:hover{background:rgba(var(--overview-accent-rgb),.52)}.schedule-list:focus-visible{outline:1px solid rgba(var(--overview-accent-rgb),.45);outline-offset:2px}
h2{display:flex;align-items:center;gap:7px}h2 svg{flex:none;color:var(--theme-primary)}
</style>
