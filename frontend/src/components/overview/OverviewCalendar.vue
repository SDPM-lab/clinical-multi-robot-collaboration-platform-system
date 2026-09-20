<script setup>
import { computed, ref, watch } from 'vue'
import { ChevronLeft, ChevronRight } from '@lucide/vue'

const props = defineProps({
  modelValue: { type: String, required: true },
  dates: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:modelValue'])
const visibleCount = 7
const windowStart = ref(0)
const selected = computed(() => props.dates.find((date) => date.key === props.modelValue) || props.dates[0])
const visibleDates = computed(() => props.dates.slice(windowStart.value, windowStart.value + visibleCount))
const maxStart = computed(() => Math.max(0, props.dates.length - visibleCount))
const shiftDates = (amount) => { windowStart.value = Math.max(0, Math.min(maxStart.value, windowStart.value + amount)) }

watch(() => props.modelValue, (key) => {
  const index = props.dates.findIndex((date) => date.key === key)
  if (index >= 0) windowStart.value = Math.max(0, Math.min(maxStart.value, index - 3))
}, { immediate: true })
</script>

<template>
  <section class="overview-calendar overview-tool-panel dashboard-panel-enter" aria-label="當日排程">
    <header>
      <div class="calendar-heading"><h2>當日排程</h2><strong>{{ selected?.month }}月{{ selected?.day }}日 · {{ selected?.weekday }}</strong></div>
      <button type="button">查看全部</button>
    </header>
    <div class="date-navigator">
      <button type="button" class="date-arrow" aria-label="較早日期" :disabled="windowStart === 0" @click="shiftDates(-1)"><ChevronLeft :size="13" /></button>
      <nav aria-label="切換排程日期">
        <button v-for="date in visibleDates" :key="date.key" type="button" :class="{ 'is-selected': date.key === modelValue, 'is-today': date.today }" :aria-label="`${date.month}月${date.day}日 ${date.weekday}`" :aria-pressed="date.key === modelValue" @click="emit('update:modelValue', date.key)"><span>{{ String(date.day).padStart(2, '0') }}</span><i :class="{ 'has-tasks': date.items?.length }"></i></button>
      </nav>
      <button type="button" class="date-arrow" aria-label="較晚日期" :disabled="windowStart >= maxStart" @click="shiftDates(1)"><ChevronRight :size="13" /></button>
    </div>
    <Transition name="schedule-fade" mode="out-in">
      <div v-if="!selected?.items?.length" :key="`${modelValue}-empty`" class="schedule-empty">本日無排程</div>
      <ol v-else :key="modelValue" class="schedule-list" tabindex="0" aria-label="當日任務列表">
        <li v-for="(item, index) in selected?.items" :key="`${item.time}-${item.title}`" :class="`is-${item.state}`" :style="{ '--schedule-index': Math.min(index, 4) }">
          <time>{{ item.time }}</time><i></i><strong>{{ item.title }}</strong><span>{{ item.assignee }}</span>
        </li>
      </ol>
    </Transition>
  </section>
</template>

<style scoped>
.overview-calendar{--panel-delay:280ms;box-sizing:border-box;display:flex;width:100%;height:100%;min-height:0;flex-direction:column;padding:14px;color:#282922}header{flex-shrink:0;display:flex;align-items:center;justify-content:space-between;gap:12px}header strong{color:#282922;font-size:13px;font-weight:550}header>button{padding:4px 0;color:var(--overview-orange);font-size:12px;background:transparent;border:0;cursor:pointer}.date-navigator{flex-shrink:0;display:grid;grid-template-columns:22px minmax(0,1fr) 22px;align-items:center;gap:4px;margin:11px 0 8px;padding-bottom:11px;border-bottom:1px solid var(--overview-border)}nav{display:grid;grid-template-columns:repeat(7,1fr);gap:3px}.date-arrow{display:grid;width:22px;height:28px;place-items:center;padding:0;color:#5f625a;background:rgba(255,255,255,.22);border:1px solid var(--overview-border);border-radius:5px;cursor:pointer}.date-arrow:hover:not(:disabled){color:var(--overview-orange);border-color:rgba(232,149,50,.26)}.date-arrow:disabled{opacity:.28;cursor:default}nav button{display:grid;height:34px;grid-template-rows:21px 4px;place-items:center;padding:4px 0 2px;color:#5f625a;background:transparent;border:0;border-radius:7px;cursor:pointer;transition:color 180ms ease,background-color 180ms ease}nav button span{font-size:12px;font-variant-numeric:tabular-nums}nav button i{width:3px;height:3px;background:transparent;border-radius:50%}nav button i.has-tasks{background:#c7b39a}nav button.is-today i,nav button.is-selected i{background:var(--overview-orange)}nav button:hover{color:var(--overview-orange)}nav button.is-selected{color:#9a5d18;background:rgba(242,164,62,.14)}ol{display:grid;min-height:0;flex:1;grid-auto-rows:minmax(52px,1fr);overflow-y:auto;overflow-x:hidden;overscroll-behavior:contain;scrollbar-gutter:stable;scrollbar-width:thin;scrollbar-color:rgba(197,139,83,.55) rgba(113,121,117,.06);margin:0;padding:0;list-style:none}li{display:grid;grid-template-columns:44px 7px minmax(0,1fr) auto;align-items:center;gap:7px;min-width:0;opacity:0;animation:schedule-enter 360ms cubic-bezier(.22,1,.36,1) calc(450ms + var(--schedule-index)*150ms) forwards}li time,li span{color:#5f625a;font-size:12px;font-variant-numeric:tabular-nums;white-space:nowrap}li strong{min-width:0;overflow:hidden;font-size:12.5px;font-weight:550;text-overflow:ellipsis;white-space:nowrap;word-break:keep-all}li>i{width:5px;height:5px;background:#c8cbc7;border-radius:50%}li.is-active>i,li.is-completed>i{background:var(--overview-orange)}.schedule-empty{display:grid;min-height:0;flex:1;place-items:center;color:#5f625a;font-size:12px}.schedule-fade-enter-active,.schedule-fade-leave-active{transition:opacity 150ms ease}.schedule-fade-enter-from,.schedule-fade-leave-to{opacity:0}
@keyframes schedule-enter{from{opacity:0;transform:translateX(6px)}to{opacity:1;transform:none}}
@media(prefers-reduced-motion:reduce){li{opacity:1;animation:none}.schedule-fade-enter-active,.schedule-fade-leave-active{transition:none}}
.calendar-heading{display:grid;gap:5px}.calendar-heading h2{margin:0;font-size:13.5px;font-weight:600}.date-navigator{animation:dashboard-fade 350ms ease 320ms both}nav button.is-selected{animation:dashboard-fade 420ms ease both}li time{font-size:11.5px}li>i{animation:dashboard-fade 200ms ease calc(720ms + var(--schedule-index)*150ms) both}li:nth-child(2)>i{background:#edc747}li:nth-child(3)>i{background:#79b58b}
.schedule-list::-webkit-scrollbar{width:6px}.schedule-list::-webkit-scrollbar-track{background:rgba(113,121,117,.06);border-radius:4px}.schedule-list::-webkit-scrollbar-thumb{background:linear-gradient(180deg,rgba(225,173,113,.7),rgba(190,125,70,.6));border:1px solid rgba(255,255,255,.5);border-radius:4px}.schedule-list::-webkit-scrollbar-thumb:hover{background:rgba(190,125,70,.8)}.schedule-list:focus-visible{outline:1px solid rgba(197,139,83,.5);outline-offset:2px}
</style>
