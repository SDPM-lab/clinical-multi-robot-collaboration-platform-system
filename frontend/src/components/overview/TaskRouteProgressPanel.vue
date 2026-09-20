<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Check, ChevronDown, MapPin } from '@lucide/vue'
import GlassPanel from './GlassPanel.vue'
import { NAVIGATION_ASSETS } from '@/config/sceneAssets.js'
import { getRobotVisualTheme } from '@/config/robotVisualThemes.js'
import { buildActiveRoutes, locationDetails } from '@/data/demoActiveRoutes.js'
import { demoFleetStore } from '@/stores/demoFleetStore.js'

const props = defineProps({ entranceDelay: { type: Number, default: 0 } })
const entranceStart = performance.now()
const emit = defineEmits(['select-task'])

const navigation = ref(null)
const selectedTaskId = ref('T001')
const errorMessage = ref('')
const animatedProgressRatio = ref(0)
const revealedThroughIndex = ref(-1)
const entranceAnimationComplete = ref(false)
const taskSelectRoot = ref(null)
const taskSelectTrigger = ref(null)
const taskSelectOpen = ref(false)
const highlightedRouteIndex = ref(0)
const TASK_PROGRESS_ANIMATION_DURATION = 650
const NODE_REVEAL_INTERVAL = 100
let animationFrameIds = []
let nodeRevealTimers = []

const routes = computed(() => navigation.value
  ? buildActiveRoutes(navigation.value, demoFleetStore.tasks.value)
  : [])
const selectedRoute = computed(() => routes.value.find((route) => route.taskId === selectedTaskId.value) || routes.value[0] || null)
const selectedTask = computed(() => demoFleetStore.tasks.value.find((task) => task.id === selectedRoute.value?.taskId) || null)
const vertexMap = computed(() => new Map((navigation.value?.vertices || []).map((vertex) => [vertex.id, vertex])))
const currentIndex = computed(() => {
  if (!selectedRoute.value?.vertexIds.length) return 0
  if (['arrived', 'completed'].includes(selectedTask.value?.status)) return selectedRoute.value.vertexIds.length - 1
  const points = selectedRoute.value.vertexIds.map((id) => vertexMap.value.get(id)).filter(Boolean)
  const lengths = points.slice(1).map((point, index) => Math.hypot(point.x - points[index].x, point.y - points[index].y))
  let remaining = lengths.reduce((sum, length) => sum + length, 0) * selectedRoute.value.progress
  let segmentIndex = 0
  while (segmentIndex < lengths.length - 1 && remaining > lengths[segmentIndex]) {
    remaining -= lengths[segmentIndex]
    segmentIndex += 1
  }
  const nearestVertexIndex = remaining > (lengths[segmentIndex] || 0) / 2 ? segmentIndex + 1 : segmentIndex
  return Math.min(selectedRoute.value.vertexIds.length - 1, nearestVertexIndex)
})
const routeStops = computed(() => (selectedRoute.value?.vertexIds || []).map((vertexId, index, vertices) => {
  const vertex = vertexMap.value.get(vertexId)
  const realLabel = vertex?.name ? locationDetails[vertex.name]?.label || vertex.name : ''
  return {
    vertexId,
    label: realLabel || `路線點 ${vertexId}`,
    state: index < currentIndex.value ? 'passed' : index === currentIndex.value ? 'current' : 'pending',
    destination: index === vertices.length - 1,
    completed: index === vertices.length - 1 && selectedTask.value?.status === 'completed',
  }
}))
const remainingCount = computed(() => Math.max(0, routeStops.value.length - currentIndex.value - 1))
const progressRatio = computed(() => routeStops.value.length <= 1
  ? 1
  : currentIndex.value / (routeStops.value.length - 1))
const panelStyle = computed(() => {
  const theme = getRobotVisualTheme(selectedRoute.value?.robotId)
  return {
    '--task-robot-color': theme.main,
    '--task-robot-soft': theme.soft,
    '--task-robot-glow': theme.glow,
    '--waypoint-count': Math.max(routeStops.value.length, 1),
    '--task-progress-ratio': animatedProgressRatio.value,
  }
})
const selectedRouteIndex = computed(() => Math.max(0, routes.value.findIndex((route) => route.taskId === selectedTaskId.value)))
const routeRobotColor = (robotId) => getRobotVisualTheme(robotId).main

const openTaskSelect = () => {
  if (!routes.value.length) return
  highlightedRouteIndex.value = selectedRouteIndex.value
  taskSelectOpen.value = true
}
const closeTaskSelect = ({ restoreFocus = false } = {}) => {
  taskSelectOpen.value = false
  if (restoreFocus) nextTick(() => taskSelectTrigger.value?.focus())
}
const chooseTask = (taskId) => {
  selectedTaskId.value = taskId
  closeTaskSelect({ restoreFocus: true })
}
const handleTaskSelectKeydown = (event) => {
  const count = routes.value.length
  if (!count) return
  if (event.key === 'Escape') {
    if (taskSelectOpen.value) {
      event.preventDefault()
      closeTaskSelect({ restoreFocus: true })
    }
    return
  }
  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    event.preventDefault()
    if (!taskSelectOpen.value) openTaskSelect()
    else highlightedRouteIndex.value = (highlightedRouteIndex.value + (event.key === 'ArrowDown' ? 1 : -1) + count) % count
    return
  }
  if (event.key === 'Home' || event.key === 'End') {
    if (!taskSelectOpen.value) return
    event.preventDefault()
    highlightedRouteIndex.value = event.key === 'Home' ? 0 : count - 1
    return
  }
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    if (!taskSelectOpen.value) openTaskSelect()
    else chooseTask(routes.value[highlightedRouteIndex.value]?.taskId)
  }
}
const onDocumentPointerDown = (event) => {
  if (!taskSelectRoot.value?.contains(event.target)) closeTaskSelect()
}

const clearEntranceAnimation = () => {
  animationFrameIds.forEach(cancelAnimationFrame)
  nodeRevealTimers.forEach(clearTimeout)
  animationFrameIds = []
  nodeRevealTimers = []
}

const playEntranceAnimation = async () => {
  clearEntranceAnimation()
  entranceAnimationComplete.value = false
  animatedProgressRatio.value = 0
  revealedThroughIndex.value = -1
  await nextTick()
  if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) {
    animatedProgressRatio.value = progressRatio.value
    revealedThroughIndex.value = currentIndex.value
    entranceAnimationComplete.value = true
    return
  }
  animationFrameIds.push(requestAnimationFrame(() => {
    animationFrameIds.push(requestAnimationFrame(() => {
      const begin = () => {
      animatedProgressRatio.value = progressRatio.value
      for (let index = 0; index <= currentIndex.value; index += 1) {
        nodeRevealTimers.push(window.setTimeout(() => {
          revealedThroughIndex.value = Math.max(revealedThroughIndex.value, index)
        }, index * NODE_REVEAL_INTERVAL))
      }
      nodeRevealTimers.push(window.setTimeout(() => {
        animatedProgressRatio.value = progressRatio.value
        revealedThroughIndex.value = currentIndex.value
        entranceAnimationComplete.value = true
      }, TASK_PROGRESS_ANIMATION_DURATION))
      }
      const remainingDelay = Math.max(0, props.entranceDelay - (performance.now() - entranceStart))
      if (remainingDelay) nodeRevealTimers.push(window.setTimeout(begin, remainingDelay))
      else begin()
    }))
  }))
}

watch(selectedTaskId, async (taskId, previousTaskId) => {
  emit('select-task', taskId)
  if (previousTaskId !== undefined) await playEntranceAnimation()
}, { immediate: true })

watch(currentIndex, (nextIndex, previousIndex) => {
  if (!entranceAnimationComplete.value || nextIndex === previousIndex) return
  animatedProgressRatio.value = progressRatio.value
  if (nextIndex > previousIndex) revealedThroughIndex.value = nextIndex
})

onMounted(async () => {
  document.addEventListener('pointerdown', onDocumentPointerDown)
  try {
    const response = await fetch(NAVIGATION_ASSETS.graph0, { cache: 'no-store' })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    navigation.value = await response.json()
    if (!routes.value.some((route) => route.taskId === selectedTaskId.value)) selectedTaskId.value = routes.value[0]?.taskId || ''
    await playEntranceAnimation()
  } catch (error) {
    errorMessage.value = `Graph 0 載入失敗：${error instanceof Error ? error.message : error}`
  }
})
onBeforeUnmount(() => {
  clearEntranceAnimation()
  document.removeEventListener('pointerdown', onDocumentPointerDown)
})
</script>

<template>
  <GlassPanel class="task-route-progress task-progress-strip" :style="panelStyle">
    <header class="task-route-progress__header">
      <div><strong>任務進度</strong><span v-if="selectedRoute">目前 {{ currentIndex + 1 }} / {{ routeStops.length }}・剩餘 {{ remainingCount }} 點</span></div>
      <div ref="taskSelectRoot" class="task-select">
        <button
          ref="taskSelectTrigger"
          type="button"
          class="task-select-trigger"
          role="combobox"
          aria-label="選擇執行中任務"
          aria-haspopup="listbox"
          :aria-expanded="taskSelectOpen"
          aria-controls="overview-task-select-listbox"
          :aria-activedescendant="taskSelectOpen ? `task-select-option-${routes[highlightedRouteIndex]?.taskId}` : undefined"
          @click="taskSelectOpen ? closeTaskSelect() : openTaskSelect()"
          @keydown="handleTaskSelectKeydown"
        >
          <span>{{ selectedRoute?.taskId }} · Robot {{ selectedRoute?.robotId?.slice(1) }}</span>
          <ChevronDown :size="14" :class="{ 'is-open': taskSelectOpen }" />
        </button>
        <div
          v-if="taskSelectOpen"
          id="overview-task-select-listbox"
          class="task-select-listbox"
          role="listbox"
          aria-label="執行中任務"
          @keydown="handleTaskSelectKeydown"
        >
          <button
            v-for="(route, index) in routes"
            :id="`task-select-option-${route.taskId}`"
            :key="route.taskId"
            type="button"
            class="task-select-option"
            role="option"
            :aria-selected="route.taskId === selectedTaskId"
            :data-highlighted="index === highlightedRouteIndex"
            @mouseenter="highlightedRouteIndex = index"
            @click="chooseTask(route.taskId)"
          >
            <i :style="{ backgroundColor: routeRobotColor(route.robotId) }" aria-hidden="true"></i>
            <span>{{ route.taskId }} · Robot {{ route.robotId.slice(1) }}</span>
          </button>
        </div>
      </div>
    </header>

    <p v-if="errorMessage" class="task-route-progress__error">{{ errorMessage }}</p>
    <template v-else-if="selectedRoute && selectedTask">
      <section class="task-route-progress__summary">
        <strong>{{ selectedTask.title }}</strong><span>{{ selectedTask.origin }} → {{ selectedTask.destination }}</span>
      </section>
      <ol class="task-route-progress__stops task-progress-track">
        <span class="task-progress-line task-progress-line--base" aria-hidden="true"></span>
        <span class="task-progress-line task-progress-line__active" aria-hidden="true"></span>
        <li
          v-for="(stop, index) in routeStops"
          :key="stop.vertexId"
          :class="[`is-${stop.state}`, { 'is-destination': stop.destination, 'is-completed': stop.completed, 'is-revealed': index <= revealedThroughIndex, 'is-reached': stop.destination && ['arrived', 'completed'].includes(selectedTask?.status) }]"
        >
          <span class="task-route-progress__node">
            <Check v-if="stop.state === 'passed'" :size="9" :stroke-width="2.4" />
            <MapPin v-else-if="stop.state === 'current'" :size="10" :stroke-width="2.2" />
          </span>
          <span><strong :title="stop.label">{{ stop.label }}</strong><small>{{ stop.state === 'passed' ? '已通過' : stop.state === 'current' ? '目前位置' : stop.destination ? '目的地' : '尚未抵達' }}</small></span>
        </li>
      </ol>
    </template>
    <p v-else class="task-route-progress__empty">目前沒有執行中的路線</p>
  </GlassPanel>
</template>

<style scoped>
.task-route-progress { display:grid; min-height:160px; grid-template-rows:auto auto minmax(0,1fr); box-sizing:border-box; padding:14px 16px 20px; overflow:visible; border-radius:var(--radius-panel); }
.task-route-progress :deep(.glass-panel__content) { display:contents; }
.task-route-progress__header { display:flex; align-items:center; justify-content:space-between; gap:12px; padding-bottom:5px; border-bottom:1px solid var(--glass-divider); }
.task-route-progress__header>div { display:flex; align-items:baseline; gap:9px; min-width:0; }
.task-route-progress__header span { color:var(--text-muted); font-size:12px; line-height:1.45; white-space:nowrap; }
.task-route-progress__header strong { color:var(--text-primary); font-size:15px; font-weight:650; }
.task-select { position:relative; z-index:12; width:172px; flex:0 0 auto; }
.task-select-trigger { display:flex; width:100%; height:32px; align-items:center; justify-content:space-between; gap:8px; padding:0 10px 0 12px; color:var(--text-primary); font-size:11px; font-weight:600; background:var(--panel-background-strong); border:1px solid var(--panel-border-subtle); border-radius:var(--radius-control); box-shadow:none; cursor:pointer; }
.task-select-trigger svg { flex:none; transition:transform 160ms ease; }.task-select-trigger svg.is-open{transform:rotate(180deg)}
.task-select-trigger:focus-visible { outline:none; border-color:var(--theme-primary-border); box-shadow:0 0 0 3px var(--focus-ring); }
.task-select-listbox { position:absolute; top:calc(100% + 5px); right:0; z-index:80; display:grid; box-sizing:border-box; width:100%; gap:2px; padding:4px; overflow:hidden; background:var(--panel-bg-strong); border:1px solid rgba(166,146,126,.32); border-radius:8px; box-shadow:var(--dropdown-shadow); backdrop-filter:blur(10px); }
.task-select-option { display:grid; grid-template-columns:8px minmax(0,1fr); min-height:30px; align-items:center; gap:8px; padding:0 8px; color:var(--text-secondary); font-size:10.5px; text-align:left; background:transparent; border:0; border-radius:var(--radius-small); cursor:pointer; }.task-select-option i{width:7px;height:7px;border-radius:50%}.task-select-option[data-highlighted='true']{color:var(--text-primary);background:var(--icon-button-hover)}.task-select-option[aria-selected='true']{color:var(--theme-primary);background:var(--theme-primary-soft)}.task-select-option:focus-visible{outline:none;background:var(--theme-primary-soft)}
.task-route-progress__summary { display:flex; align-items:center; gap:7px; padding:6px 1px 3px; overflow:hidden; font-size:12px; line-height:1.45; white-space:nowrap; }
.task-route-progress__summary>strong { color:var(--text-primary); font-size:12px; }
.task-route-progress__summary>span { overflow:hidden; color:var(--text-secondary); font-size:12px; text-overflow:ellipsis; }
.task-route-progress__stops { position:relative; display:grid; grid-template-columns:repeat(var(--waypoint-count),minmax(0,1fr)); align-items:start; width:100%; min-height:72px; box-sizing:border-box; margin:0; padding:8px 4px 22px; overflow:visible; list-style:none; }
.task-route-progress__stops li { position:relative; z-index:2; display:grid; min-width:0; justify-items:center; gap:7px; text-align:center; }
.task-progress-line { position:absolute; z-index:0; top:17px; right:calc(50% / var(--waypoint-count)); left:calc(50% / var(--waypoint-count)); height:2px; border-radius:999px; pointer-events:none; }
.task-progress-line--base { background:var(--glass-divider); }
.task-progress-line__active { background:var(--task-robot-color); opacity:.58; transform:scaleX(var(--task-progress-ratio)); transform-origin:left center; transition:transform 650ms cubic-bezier(.22,1,.36,1); }
.task-route-progress__node { position:relative; z-index:1; display:grid; width:18px; height:18px; place-items:center; box-sizing:border-box; color:transparent; background:var(--panel-bg-strong); border:1.5px solid var(--text-muted); border-radius:50%; opacity:.82; transform:scale(.92); transition:color 220ms ease,background-color 220ms ease,border-color 220ms ease,box-shadow 260ms ease,opacity 260ms ease,transform 320ms cubic-bezier(.22,1,.36,1); }
.task-route-progress__stops li.is-revealed .task-route-progress__node { opacity:1; transform:scale(1); }
.task-route-progress__stops li.is-passed.is-revealed .task-route-progress__node { color:#fff; background:var(--task-robot-color); border-color:var(--task-robot-color); }
.task-route-progress__stops li.is-current.is-revealed .task-route-progress__node { color:#fff; background:var(--task-robot-color); border-color:color-mix(in srgb,var(--task-robot-color) 70%,white); box-shadow:0 0 0 4px var(--task-robot-soft),0 0 12px color-mix(in srgb,var(--task-robot-glow) 40%,transparent); animation:current-stop-pulse 1.8s ease-in-out 1; }
.task-route-progress__stops li.is-destination .task-route-progress__node { border-radius:3px; }
.task-route-progress__stops li.is-destination:not(.is-reached) .task-route-progress__node { color:transparent; background:var(--panel-bg-strong); border-color:var(--text-muted); }
.task-route-progress__stops li.is-reached.is-revealed .task-route-progress__node { color:#fff; background:var(--task-robot-color); border-color:var(--task-robot-color); }
.task-route-progress__stops li>span:last-child { display:grid; width:100%; min-width:0; gap:0; padding:0 4px; box-sizing:border-box; }
.task-route-progress__stops strong { overflow:hidden; color:var(--text-primary); font-size:12px; line-height:1.3; font-weight:600; text-overflow:ellipsis; white-space:nowrap; }
.task-route-progress__stops small { display:block; margin-top:4px; color:var(--text-muted); font-size:11px; line-height:1.35; white-space:nowrap; }
.task-route-progress__error,.task-route-progress__empty { margin:12px 2px; color:var(--text-secondary); font-size:11.5px; line-height:1.5; }
@keyframes current-stop-pulse { 50% { transform:scale(1.08); box-shadow:0 0 0 5px var(--task-robot-soft),0 0 16px color-mix(in srgb,var(--task-robot-glow) 48%,transparent); } }
@media (max-width:1199px) and (min-width:701px) { .task-route-progress { padding-right:9px; padding-left:9px; }.task-route-progress__stops strong{font-size:9.5px}.task-route-progress__stops li>span:last-child{padding:0 2px} }
@media (prefers-reduced-motion:reduce) { .task-progress-line__active,.task-route-progress__node { transition:none; animation:none!important; } }
</style>
