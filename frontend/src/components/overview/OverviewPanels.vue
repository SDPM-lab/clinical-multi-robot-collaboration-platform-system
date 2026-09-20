<script setup>
import { computed, onActivated, onBeforeUnmount, onMounted, provide, ref } from 'vue'
import {
  getAverageBattery,
  getTaskCompletion,
  overviewDemoData,
} from '@/data/overviewDemoData.js'
import FleetOverviewPanel from './FleetOverviewPanel.vue'
import RobotStatusPanel from './RobotStatusPanel.vue'
import SystemSummaryPanel from './SystemSummaryPanel.vue'
import TaskCompletionPanel from './TaskCompletionPanel.vue'
import TaskRouteProgressPanel from './TaskRouteProgressPanel.vue'
import TodaySchedulePanel from './TodaySchedulePanel.vue'
import TodayTasksPanel from './TodayTasksPanel.vue'

const props = defineProps({
  data: { type: Object, default: () => overviewDemoData },
  visiblePanels: {
    type: Object,
    default: () => ({
      tasks: true,
      completion: true,
      taskProgress: true,
      schedule: true,
      fleet: true,
      summary: true,
      robots: true,
    }),
  },
})
const emit = defineEmits(['open-robot-status', 'select-task'])

provide('overviewEntranceDelay', 1050)
const animationKey = ref(0)
const animationsPlaying = ref(false)
const taskCompletion = computed(() => getTaskCompletion(props.data.tasks))
const averageBattery = computed(() => getAverageBattery(props.data.robots))
let firstFrameId
let secondFrameId
let lastReplayAt = -Infinity

const cancelStagingFrames = () => {
  cancelAnimationFrame(firstFrameId)
  cancelAnimationFrame(secondFrameId)
}

const replayOverviewAnimations = () => {
  const now = performance.now()
  if (now - lastReplayAt < 50) return
  lastReplayAt = now
  cancelStagingFrames()
  animationsPlaying.value = false
  animationKey.value += 1

  if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) {
    animationsPlaying.value = true
    return
  }

  firstFrameId = requestAnimationFrame(() => {
    secondFrameId = requestAnimationFrame(() => {
      animationsPlaying.value = true
    })
  })
}

onMounted(replayOverviewAnimations)
onActivated(replayOverviewAnimations)
onBeforeUnmount(cancelStagingFrames)
</script>

<template>
  <aside class="overview-panels" aria-label="首頁資訊摘要">
    <div v-if="visiblePanels.completion !== false" class="completion-float">
      <div class="panel-surface" :class="{ 'panel-surface--playing': animationsPlaying }">
        <TaskCompletionPanel
          :completion="taskCompletion"
          :animation-key="animationKey"
        />
      </div>
    </div>
    <div class="quick-log-slot"><slot name="quick-log" /></div>
    <div v-if="visiblePanels.schedule !== false" class="schedule-float">
      <div class="panel-surface" :class="{ 'panel-surface--playing': animationsPlaying }">
        <TodaySchedulePanel />
      </div>
    </div>
    <div v-if="visiblePanels.taskProgress !== false" class="task-progress-float">
      <div class="panel-surface panel-surface--playing"><TaskRouteProgressPanel :entrance-delay="650" @select-task="emit('select-task', $event)" /></div>
    </div>
    <div class="dashboard-dock">
      <div v-if="visiblePanels.tasks !== false" class="panel-slot today-tasks-panel">
        <div class="panel-surface" :class="{ 'panel-surface--playing': animationsPlaying }">
          <TodayTasksPanel
            :data="data.tasks"
            :completion="taskCompletion"
            :animation-key="animationKey"
          />
        </div>
      </div>
      <div v-if="visiblePanels.fleet !== false" class="panel-slot fleet-overview-panel">
        <div class="panel-surface" :class="{ 'panel-surface--playing': animationsPlaying }">
          <FleetOverviewPanel :data="data.fleet" :animation-key="animationKey" />
        </div>
      </div>
      <div v-if="visiblePanels.summary !== false" class="panel-slot system-summary-panel">
        <div class="panel-surface" :class="{ 'panel-surface--playing': animationsPlaying }">
          <SystemSummaryPanel :data="data.system" :animation-key="animationKey" />
        </div>
      </div>
      <div v-if="visiblePanels.robots !== false" class="panel-slot robot-status-panel">
        <div class="panel-surface" :class="{ 'panel-surface--playing': animationsPlaying }">
          <RobotStatusPanel
            :data="data.robots"
            :average-battery="averageBattery"
            :animation-key="animationKey"
            @open-robot-status="emit('open-robot-status')"
          />
        </div>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.overview-panels {
  position: absolute;
  z-index: 20;
  inset: 70px var(--overview-content-right) 18px var(--overview-content-left);
  display:grid;
  grid-template-columns:108px minmax(0,1fr) var(--overview-calendar-width);
  grid-template-rows:112px 166px minmax(250px,1fr);
  gap:16px var(--overview-column-gap);
  min-height:0;
  padding-top:54px;
  pointer-events: none;
}

.completion-float {
  grid-area:1 / 1;
  width: 108px;
  height: 112px;
  pointer-events: auto;
  --entry-delay: 400ms;
}
.quick-log-slot{animation:composer-enter 600ms cubic-bezier(.16,1,.3,1) 400ms both;grid-area:1 / 2;min-width:0;pointer-events:auto}.quick-log-slot :deep(.quick-log-composer){position:relative;inset:auto;width:100%;height:112px;min-height:0;transform:none}

.schedule-float {
  grid-area:1 / 3 / span 2;
  width: var(--overview-calendar-width);
  height:auto;
  pointer-events: auto;
  --entry-delay: 500ms;
}

.task-progress-float {
  grid-area:2 / 1 / 3 / 3;
  width:auto;
  height:auto;
  min-height:0;
  min-width:0;
  pointer-events:auto;
  --entry-delay:650ms;
}

.dashboard-dock {
  grid-area:3 / 1 / 4 / 4;
  box-sizing: border-box;
  display: grid;
  grid-template-columns:
    repeat(3, minmax(250px, 1fr))
    minmax(440px, 1.45fr);
  gap: 12px;
  width: 100%;
  height: 100%;
  min-height:0;
  pointer-events: auto;
  transform: none;
}

.panel-slot {
  min-width: 0;
  height: 100%;
  align-self: stretch;
}

.panel-surface {
  width: 100%;
  height: 100%;
  opacity: 0;
}

.panel-surface--playing {
  animation: panel-enter 470ms cubic-bezier(.16,1,.3,1) var(--entry-delay) both;
}

.panel-surface :deep(.glass-panel) { height: 100%; }

.today-tasks-panel { --entry-delay: 900ms; }
.fleet-overview-panel { --entry-delay: 1010ms; }
.system-summary-panel { --entry-delay: 1120ms; }
.robot-status-panel { --entry-delay: 1230ms; }

@keyframes composer-enter { from { opacity:0; translate:0 -10px; } to { opacity:1; translate:0 0; } }

@keyframes panel-enter {
  from { opacity: 0; transform: translateY(8px) scale(0.985); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

@media (min-width: 900px) and (max-width: 1279px) {
  .overview-panels{grid-template-columns:108px minmax(0,1fr) 270px;padding-top:54px}
  .dashboard-dock {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    min-height:528px;
    overflow-y:auto;
  }

  .panel-slot { height: 260px; }
}

@media (max-width: 899px) {
  .overview-panels{inset:66px 0 0;display:block;padding-top:0}
  .quick-log-slot :deep(.quick-log-composer){position:absolute;top:98px;left:50%;width:clamp(460px,70vw,590px);height:auto;transform:translateX(-50%)}
  .completion-float{position:absolute;top:58px;left:18px}
  .schedule-float{position:absolute;top:58px;right:18px;width:292px;height:292px}
  .task-progress-float { position:absolute;top:270px;right:18px;bottom:auto;left:18px;height:142px; }
  .dashboard-dock {
    position:absolute;
    right: 0;
    bottom: 16px;
    left: 0;
    display: flex;
    width: auto;
    height: 276px;
    padding: 0 18px 8px;
    overflow-x: auto;
    overflow-y: hidden;
    scroll-padding-inline: 18px;
    scroll-snap-type: x proximity;
    transform: none;
  }

  .panel-slot {
    flex: 0 0 min(82vw, 340px);
    min-width: 280px;
    height: 260px;
    scroll-snap-align: start;
  }

  .robot-status-panel { flex-basis: min(88vw, 390px); min-width: 340px; }
}

@media (min-width:1200px) and (min-height:850px){.overview-panels{grid-template-rows:112px 174px clamp(300px,31vh,330px);gap:24px var(--overview-column-gap);padding-top:clamp(34px,6vh,64px)}}

@media (max-width: 700px) {
  .quick-log-slot :deep(.quick-log-composer){width:calc(100vw - 24px)}
  .completion-float {
    left: 12px;
    width: min(126px, calc(100vw - 24px));
  }

  .schedule-float {
    top: 404px;
    right: 18px;
    width: min(292px, calc(100vw - 36px));
  }

  .task-progress-float { top:270px; right:12px; bottom:auto; left:12px; width:auto; height:142px; }
}

@media (prefers-reduced-motion: reduce) {
  .quick-log-slot,
  .panel-surface,
  .panel-surface--playing {
    opacity: 1;
    animation: none;
  }
}
</style>
