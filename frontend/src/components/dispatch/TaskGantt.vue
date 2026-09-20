<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { getRobotVisualTheme } from '@/config/robotVisualThemes.js'
import { secondsToTime, timeToSeconds } from '@/stores/demoFleetStore.js'
import TaskBubble from './TaskBubble.vue'
import TaskDurationRange from './TaskDurationRange.vue'
import TimelineAxis from './TimelineAxis.vue'
import {
  WORKDAY_END, WORKDAY_START, TICK_STEPS, assignBubbleLevels, getAnchoredScrollLeft,
  getDragSnapSeconds, hasTimelineConflict, normalizePriority, priorityBubbleSize,
  shiftIsoDate, snapTaskStart,
} from './taskTimeline.js'

const props = defineProps({
  robots: { type: Array, required: true }, tasks: { type: Array, required: true }, date: { type: String, required: true },
})
const emit = defineEmits(['update:date', 'save-changes'])
const viewport = ref(null)
const viewportWidth = ref(900)
const zoom = ref(2)
const isScheduleEditing = ref(false)
const drafts = ref({})
const snapshot = ref({})
const dragging = ref(null)
const panning = ref(null)
const warning = ref(null)
const selectedTask = ref(null)
const pendingDate = ref('')
const dateDialogOpen = ref(false)
let resizeObserver
let initialScrollApplied = false

const WORKDAY_DURATION = WORKDAY_END - WORKDAY_START
const STAGE_HEIGHT = 210
const BASELINE_Y = 105
const MIN_SCALE = 1
const MAX_SCALE = 18
const priorityLabels = Object.freeze({ low: '低', normal: '一般', high: '高' })
const unassignedTheme = Object.freeze({ main: '#A8ACAA', soft: 'rgba(168,172,170,.18)' })

const timelineWidth = computed(() => Math.max(viewportWidth.value, 1) * zoom.value)
const pixelsPerMinute = computed(() => timelineWidth.value / (WORKDAY_DURATION / 60))
const labelMode = computed(() => pixelsPerMinute.value >= 24 ? 'full' : pixelsPerMinute.value >= 12 ? 'short' : 'code')
const dragSnapSeconds = computed(() => getDragSnapSeconds(pixelsPerMinute.value))
const tickStep = computed(() => pixelsPerMinute.value >= 24 ? TICK_STEPS.detail : pixelsPerMinute.value >= 12 ? TICK_STEPS.close : pixelsPerMinute.value >= 5 ? TICK_STEPS.normal : TICK_STEPS.far)
const majorStep = computed(() => tickStep.value === TICK_STEPS.detail ? 60 : tickStep.value === TICK_STEPS.close ? 5 * 60 : 30 * 60)
const ticks = computed(() => {
  const values = []
  for (let second = WORKDAY_START; second <= WORKDAY_END; second += tickStep.value) values.push({ second, major: second % majorStep.value === 0 })
  return values
})
const labels = computed(() => ticks.value.filter((tick) => tick.major))
const hasChanges = computed(() => props.tasks.some((task) => drafts.value[task.id] !== undefined && drafts.value[task.id] !== snapshot.value[task.id]))
const zoomDescription = computed(() => `${pixelsPerMinute.value.toFixed(1)} px/分鐘 · ${tickStep.value} 秒刻度`)
const now = new Date()
const todayIso = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 12).toISOString().slice(0, 10)
const nowSeconds = now.getHours() * 3600 + now.getMinutes() * 60 + now.getSeconds()
const nowVisible = computed(() => props.date === todayIso && nowSeconds >= WORKDAY_START && nowSeconds <= WORKDAY_END)
const dateLabel = computed(() => new Intl.DateTimeFormat('zh-TW', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' }).format(new Date(`${props.date}T12:00:00`)).replace('星期', '・星期'))

const positionPercent = (seconds) => ((seconds - WORKDAY_START) / WORKDAY_DURATION) * 100
const displayedStart = (task) => dragging.value?.task.id === task.id ? dragging.value.previewStart : drafts.value[task.id] ?? timeToSeconds(task.startTime)
const normalizedPriority = (task) => normalizePriority(task.priority)
const bubbleSize = (task) => priorityBubbleSize[normalizedPriority(task)]
const taskTheme = (task) => ['R01', 'R02', 'R03'].includes(task.robotId) ? getRobotVisualTheme(task.robotId) : unassignedTheme
const taskVariables = (task) => ({ '--task-main': taskTheme(task).main, '--task-soft': taskTheme(task).soft, '--bubble-ink': task.robotId === 'R01' ? '#fff' : '#27302e' })
const bubbleItems = computed(() => assignBubbleLevels(props.tasks.map((task) => ({ task, startSeconds: displayedStart(task), size: bubbleSize(task) })), WORKDAY_DURATION / timelineWidth.value))
const bubbleLayout = computed(() => new Map(bubbleItems.value.map((item) => [item.task.id, item])))
const bubbleY = (task) => {
  const level = bubbleLayout.value.get(task.id)?.level || -1
  const raw = BASELINE_Y + Math.sign(level) * (44 + (Math.abs(level) - 1) * 28)
  return Math.max(bubbleSize(task) / 2 + 4, Math.min(STAGE_HEIGHT - bubbleSize(task) / 2 - 4, raw))
}
const durationStyle = (task) => ({ ...taskVariables(task), top: `${BASELINE_Y}px`, left: `${positionPercent(displayedStart(task))}%`, width: `${(task.durationSeconds / WORKDAY_DURATION) * 100}%` })
const connectorStyle = (task) => {
  const y = bubbleY(task)
  const edge = y < BASELINE_Y ? y + bubbleSize(task) / 2 : y - bubbleSize(task) / 2
  return { left: `${positionPercent(displayedStart(task))}%`, top: `${Math.min(edge, BASELINE_Y)}px`, height: `${Math.abs(BASELINE_Y - edge)}px`, background: taskTheme(task).main }
}
const bubbleStyle = (task) => ({ ...taskVariables(task), left: `${positionPercent(displayedStart(task))}%`, top: `${bubbleY(task)}px` })
const canDragTask = (task) => isScheduleEditing.value && task.status !== 'completed'
const robotFor = (task) => props.robots.find((robot) => robot.id === task.robotId)
const taskClasses = (task) => ({ 'has-warning': warning.value?.taskId === task.id, 'is-offline': robotFor(task)?.state === 'offline' })

const centerOn = async (seconds) => {
  await nextTick()
  if (viewport.value) viewport.value.scrollLeft = Math.max(0, positionPercent(seconds) / 100 * timelineWidth.value - viewportWidth.value / 2)
}
const setZoom = async (nextZoom, cursorX = viewportWidth.value / 2) => {
  const clamped = Math.max(MIN_SCALE, Math.min(MAX_SCALE, nextZoom))
  if (clamped === zoom.value || !viewport.value) return
  const nextScroll = getAnchoredScrollLeft({ oldZoom: zoom.value, newZoom: clamped, viewportWidth: viewportWidth.value, scrollLeft: viewport.value.scrollLeft, cursorX })
  zoom.value = clamped
  await nextTick()
  viewport.value.scrollLeft = nextScroll
}
const onTimelineWheel = (event) => {
  event.preventDefault()
  event.stopPropagation()
  if (!viewport.value) return
  if (event.shiftKey || Math.abs(event.deltaX) > Math.abs(event.deltaY)) { viewport.value.scrollLeft += event.deltaX || event.deltaY; return }
  const rect = viewport.value.getBoundingClientRect()
  const cursorX = Math.max(0, Math.min(rect.width, event.clientX - rect.left))
  setZoom(zoom.value * (event.deltaY < 0 ? 1.12 : 0.89), cursorX)
}
const zoomAtPointer = (event) => {
  const rect = viewport.value.getBoundingClientRect()
  setZoom(zoom.value * 1.4, Math.max(0, Math.min(rect.width, event.clientX - rect.left)))
}
const enterEditing = () => {
  snapshot.value = Object.fromEntries(props.tasks.map((task) => [task.id, timeToSeconds(task.startTime)]))
  drafts.value = { ...snapshot.value }
  warning.value = null
  selectedTask.value = null
  isScheduleEditing.value = true
}
const cancelEditing = () => { drafts.value = { ...snapshot.value }; warning.value = null; dragging.value = null; isScheduleEditing.value = false }
const saveEditing = () => {
  const changes = props.tasks.filter((task) => drafts.value[task.id] !== snapshot.value[task.id]).map((task) => ({ taskId: task.id, startSeconds: drafts.value[task.id] }))
  emit('save-changes', changes, (result) => {
    if (!result.ok) { warning.value = { taskId: result.taskId, message: result.reason }; return }
    isScheduleEditing.value = false
    warning.value = null
  })
}
const beginDrag = (event, task) => {
  if (!canDragTask(task)) { selectedTask.value = task; return }
  event.preventDefault()
  event.currentTarget.setPointerCapture(event.pointerId)
  const start = drafts.value[task.id] ?? timeToSeconds(task.startTime)
  dragging.value = { task, originX: event.clientX, originalStart: start, previewStart: start, pointerId: event.pointerId }
}
const dragTask = (event) => {
  if (!dragging.value || event.pointerId !== dragging.value.pointerId) return
  const deltaSeconds = ((event.clientX - dragging.value.originX) / timelineWidth.value) * WORKDAY_DURATION
  dragging.value.previewStart = snapTaskStart(dragging.value.originalStart + deltaSeconds, dragging.value.task.durationSeconds, dragSnapSeconds.value)
}
const endDrag = () => {
  if (!dragging.value) return
  const { task, previewStart } = dragging.value
  const reason = hasTimelineConflict({ task, startSeconds: previewStart, drafts: drafts.value, tasks: props.tasks, robots: props.robots })
  if (reason) warning.value = { taskId: task.id, message: reason }
  else { drafts.value = { ...drafts.value, [task.id]: previewStart }; warning.value = null }
  dragging.value = null
}
const beginPan = (event) => {
  if (event.target.closest('.task-bubble')) return
  panning.value = { pointerId: event.pointerId, originX: event.clientX, scrollLeft: viewport.value.scrollLeft }
  event.currentTarget.setPointerCapture(event.pointerId)
}
const panTimeline = (event) => { if (panning.value?.pointerId === event.pointerId) viewport.value.scrollLeft = panning.value.scrollLeft - (event.clientX - panning.value.originX) }
const endPan = () => { panning.value = null }
const requestDate = (nextDate) => {
  if (nextDate === props.date) { centerOn(nextDate === todayIso ? nowSeconds : 11 * 3600); return }
  if (isScheduleEditing.value && hasChanges.value) { pendingDate.value = nextDate; dateDialogOpen.value = true; return }
  if (isScheduleEditing.value) cancelEditing()
  emit('update:date', nextDate)
}
const discardAndSwitchDate = () => { cancelEditing(); emit('update:date', pendingDate.value); pendingDate.value = ''; dateDialogOpen.value = false }

watch(() => props.tasks, () => { if (!isScheduleEditing.value) drafts.value = {} }, { deep: true })
watch(() => props.date, () => centerOn(props.date === todayIso ? nowSeconds : 11 * 3600))
onMounted(() => {
  resizeObserver = new ResizeObserver(async ([entry]) => {
    viewportWidth.value = Math.max(entry.contentRect.width, 1)
    if (!initialScrollApplied && viewport.value) { initialScrollApplied = true; await centerOn(nowVisible.value ? nowSeconds : 11 * 3600) }
  })
  if (viewport.value) { resizeObserver.observe(viewport.value); viewport.value.addEventListener('wheel', onTimelineWheel, { passive: false }) }
})
onBeforeUnmount(() => { resizeObserver?.disconnect(); viewport.value?.removeEventListener('wheel', onTimelineWheel) })
</script>

<template>
  <section class="timeline-panel" aria-label="機器人任務泡泡時間軸">
    <div class="timeline-toolbar">
      <div class="date-navigation"><button type="button" @click="requestDate(shiftIsoDate(date, -1))">〈 前一天</button><strong>{{ dateLabel }}</strong><button type="button" @click="requestDate(shiftIsoDate(date, 1))">後一天 〉</button></div>
      <div class="timeline-actions">
        <button type="button" @click="requestDate(todayIso)">今天</button>
        <label class="date-picker"><span class="sr-only">選擇日期</span><input :value="date" type="date" @change="requestDate($event.target.value)"></label>
        <span class="zoom-label">滾輪縮放 · {{ zoomDescription }}</span>
        <button v-if="!isScheduleEditing" type="button" class="edit-button" @click="enterEditing">編輯排程</button>
        <template v-else><button type="button" class="edit-button active" aria-pressed="true">編輯中</button><button type="button" @click="cancelEditing">取消</button><button type="button" class="save-button" :disabled="!hasChanges" @click="saveEditing">儲存變更</button></template>
      </div>
    </div>
    <div class="timeline-legend">
      <span v-for="robot in robots.slice(0, 3)" :key="robot.id"><i :style="{ background: getRobotVisualTheme(robot.id).main }"></i>{{ robot.name }}</span>
      <span class="priority-key"><i class="size-low"></i>小：低　<i class="size-normal"></i>中：一般　<i class="size-high"></i>大：高</span>
      <em v-if="isScheduleEditing">拖曳 Bubble 改時間 · Snap {{ dragSnapSeconds }} 秒</em>
    </div>
    <div class="timeline-grid" :class="{ 'is-editing': isScheduleEditing }">
      <div ref="viewport" class="time-viewport">
        <div class="time-canvas" :style="{ width: `${timelineWidth}px` }">
          <TimelineAxis :ticks="ticks" :labels="labels" :position-percent="positionPercent" :format-time="secondsToTime" />
          <div class="bubble-stage" @pointerdown="beginPan" @pointermove="panTimeline" @pointerup="endPan" @pointercancel="endPan" @dblclick="zoomAtPointer">
            <i v-for="tick in ticks" :key="`stage-${tick.second}`" class="stage-tick" :class="{ major: tick.major }" :style="{ left: `${positionPercent(tick.second)}%` }"></i>
            <i class="timeline-baseline"></i>
            <template v-for="task in tasks" :key="task.id">
              <TaskDurationRange :style="durationStyle(task)" :selected="selectedTask?.id === task.id" />
              <i class="bubble-connector" :style="connectorStyle(task)"></i>
              <i v-if="dragging?.task.id === task.id" class="bubble-ghost" :style="{ ...taskVariables(task), left: `${positionPercent(dragging.originalStart)}%`, top: `${bubbleY(task)}px`, width: `${bubbleSize(task)}px`, height: `${bubbleSize(task)}px` }"></i>
              <TaskBubble :task="task" :size="bubbleSize(task)" :label-mode="labelMode" :start-time="secondsToTime(displayedStart(task))" :end-time="secondsToTime(displayedStart(task) + task.durationSeconds)" :priority-label="priorityLabels[normalizedPriority(task)]" :editing="isScheduleEditing" :dragging="dragging?.task.id === task.id" :disabled="task.status === 'completed'" :placement="bubbleY(task) < BASELINE_Y ? 'above' : 'below'" :class="taskClasses(task)" :style="bubbleStyle(task)" @pointerdown="beginDrag($event, task)" @pointermove="dragTask" @pointerup="endDrag" @pointercancel="endDrag" />
            </template>
            <template v-if="dragging"><i class="drag-guide" :style="{ left: `${positionPercent(dragging.previewStart)}%` }"></i><time class="drag-time" :style="{ left: `${positionPercent(dragging.previewStart)}%` }">{{ secondsToTime(dragging.previewStart) }} → {{ secondsToTime(dragging.previewStart + dragging.task.durationSeconds) }}</time></template>
            <template v-if="nowVisible"><i class="now-line" :style="{ left: `${positionPercent(nowSeconds)}%` }"></i><time class="now-label" :style="{ left: `${positionPercent(nowSeconds)}%` }">{{ secondsToTime(nowSeconds) }}</time></template>
          </div>
        </div>
      </div>
    </div>
    <div v-if="warning" class="timeline-warning" role="alert">{{ warning.message }}</div>
    <article v-if="selectedTask && !isScheduleEditing" class="task-detail-popover"><button type="button" aria-label="關閉" @click="selectedTask=null">×</button><strong>{{ selectedTask.id }} · {{ selectedTask.title }}</strong><span>{{ selectedTask.startTime }}–{{ selectedTask.endTime }}</span><span>{{ selectedTask.origin }} → {{ selectedTask.destination }}</span><span>{{ priorityLabels[normalizedPriority(selectedTask)] }}優先級 · {{ selectedTask.status }}</span></article>
    <div v-if="dateDialogOpen" class="unsaved-dialog-backdrop"><article class="unsaved-dialog" role="dialog" aria-modal="true"><strong>目前有尚未儲存的排程變更</strong><div><button type="button" class="discard-button" @click="discardAndSwitchDate">放棄變更</button><button type="button" @click="dateDialogOpen=false">繼續編輯</button></div></article></div>
  </section>
</template>

<style scoped>
.timeline-panel{position:relative;box-sizing:border-box;display:grid;grid-template-rows:44px 27px minmax(0,1fr);min-height:0;padding:9px 14px 12px;color:var(--text-primary);background:linear-gradient(145deg,rgba(255,255,255,.28),rgba(255,255,255,.035)),var(--panel-bg);border:1px solid var(--panel-border);border-radius:12px;box-shadow:var(--glass-shadow);backdrop-filter:blur(22px) saturate(112%)}
.timeline-toolbar{display:grid;grid-template-columns:minmax(360px,1fr) auto;align-items:center;gap:12px;min-height:44px}.date-navigation{display:flex;align-items:center;justify-content:flex-start;gap:14px}.date-navigation strong{min-width:230px;font-size:14px;text-align:center}.timeline-toolbar button,.date-picker{display:inline-flex;align-items:center;justify-content:center;min-height:29px;padding:5px 9px;color:var(--text-secondary);font-size:12px;background:transparent;border:1px solid transparent;border-radius:6px;cursor:pointer}.timeline-toolbar button:hover,.timeline-toolbar button:focus-visible,.date-picker:hover{color:var(--text-primary);background:var(--icon-button-hover);border-color:var(--panel-border)}.date-picker input{width:108px;color:var(--text-secondary);font:inherit;background:transparent;border:0;outline:0}.timeline-actions{display:flex;align-items:center;justify-content:flex-end;gap:4px;color:var(--text-muted);font-size:11.5px;white-space:nowrap}.zoom-label{margin:0 7px;color:var(--text-muted);font-size:10.5px}.edit-button,.save-button{margin-left:7px!important;color:var(--accent-orange)!important;border-color:color-mix(in srgb,var(--accent-orange) 34%,transparent)!important}.save-button{color:#fff!important;background:var(--accent-orange)!important}.save-button:disabled{opacity:.42;cursor:not-allowed}.edit-button.active{background:color-mix(in srgb,var(--accent-orange) 10%,transparent)!important}
.timeline-legend{display:flex;align-items:center;gap:14px;min-height:27px;color:var(--text-muted);font-size:10.5px;border-bottom:1px solid var(--glass-divider)}.timeline-legend span{display:flex;align-items:center;gap:5px;white-space:nowrap}.timeline-legend i{display:inline-block;width:7px;height:7px;border-radius:50%}.timeline-legend .priority-key{margin-left:auto}.priority-key .size-low{width:7px;height:7px;border:1px solid currentColor;background:transparent}.priority-key .size-normal{width:10px;height:10px;border:1px solid currentColor;background:transparent}.priority-key .size-high{width:13px;height:13px;border:1px solid currentColor;background:transparent}.timeline-legend em{color:var(--accent-orange);font-style:normal}
.timeline-grid{min-height:0;overflow:hidden}.time-viewport{height:100%;min-width:0;overflow-x:auto;overflow-y:hidden;overscroll-behavior:contain;scrollbar-width:thin}.time-canvas{height:242px;min-width:100%}.bubble-stage{position:relative;height:210px;overflow:visible;cursor:grab;touch-action:none}.bubble-stage:active{cursor:grabbing}.stage-tick{position:absolute;z-index:0;top:0;bottom:0;width:1px;background:color-mix(in srgb,var(--glass-divider) 25%,transparent);pointer-events:none}.stage-tick.major{background:color-mix(in srgb,var(--glass-divider) 55%,transparent)}.timeline-baseline{position:absolute;z-index:2;top:105px;right:0;left:0;height:1px;background:color-mix(in srgb,var(--text-muted) 34%,transparent);pointer-events:none}.bubble-connector{position:absolute;z-index:4;width:1px;opacity:.52;pointer-events:none;transform:translateX(-50%)}.bubble-ghost{position:absolute;z-index:5;background:var(--task-soft);border:1px dashed var(--task-main);border-radius:50%;opacity:.52;transform:translate(-50%,-50%);pointer-events:none}.drag-guide{position:absolute;z-index:15;top:0;bottom:0;width:1px;background:var(--accent-orange);pointer-events:none}.drag-time{position:absolute;z-index:16;top:4px;padding:3px 5px;color:#fff;font-size:9px;font-variant-numeric:tabular-nums;white-space:nowrap;background:var(--accent-orange);border-radius:4px;transform:translateX(-50%);pointer-events:none}.now-line{position:absolute;z-index:10;top:0;bottom:0;width:1.5px;background:#d94b55;pointer-events:none}.now-label{position:absolute;z-index:11;top:3px;padding:2px 5px;color:#fff;font-size:9px;background:#d94b55;border-radius:4px;transform:translateX(-50%);pointer-events:none}
:deep(.task-bubble.has-warning){outline:2px solid #d94b55}:deep(.task-bubble.is-offline){filter:grayscale(1);opacity:.58}
.timeline-warning{position:absolute;right:16px;bottom:8px;z-index:25;padding:6px 9px;color:#b23d47;font-size:11px;background:var(--popover-bg);border:1px solid rgba(217,75,85,.3);border-radius:8px;box-shadow:var(--control-shadow)}.task-detail-popover{position:absolute;z-index:30;right:16px;bottom:12px;display:grid;width:220px;gap:4px;padding:12px;color:var(--text-secondary);font-size:11.5px;background:var(--popover-bg);border:1px solid var(--panel-border);border-radius:11px;box-shadow:var(--dropdown-shadow)}.task-detail-popover strong{color:var(--text-primary)}.task-detail-popover button{position:absolute;top:5px;right:7px;color:var(--text-muted);background:transparent;border:0;cursor:pointer}.unsaved-dialog-backdrop{position:absolute;z-index:40;inset:0;display:grid;place-items:center;background:rgba(40,42,40,.16);backdrop-filter:blur(3px)}.unsaved-dialog{display:grid;gap:14px;padding:17px 18px;background:var(--panel-bg-strong);border:1px solid var(--panel-border);border-radius:13px;box-shadow:var(--dropdown-shadow)}.unsaved-dialog>div{display:flex;justify-content:flex-end;gap:8px}.unsaved-dialog button{padding:7px 10px;color:var(--text-primary);background:var(--icon-button-background);border:1px solid var(--panel-border);border-radius:8px;cursor:pointer}.discard-button{color:#b23d47!important}.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0)}
@media(max-width:1100px){.timeline-toolbar{grid-template-columns:1fr}.timeline-actions{justify-content:flex-start}.zoom-label{display:none}.timeline-legend{gap:8px}.timeline-legend .priority-key{display:none}}
</style>
