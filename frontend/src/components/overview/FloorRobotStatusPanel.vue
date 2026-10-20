<script setup>
import { overviewRobotColors, overviewThemeVars } from '@/styles/overviewTheme.js'
import { computed, reactive, ref } from 'vue'
import { Maximize2, X } from '@lucide/vue'
import RobotBatteryTrend from './RobotBatteryTrend.vue'
import { batteryRanges, fixedDemoBatteryHistory, robotStatusLabels, selectBatteryHistory } from '@/data/robotBatteryTrend.js'

const props = defineProps({
  history: { type: Array, default: () => [] },
  rollingHistory: { type: Object, default: () => ({}) },
  floor: { type: String, required: true },
  robots: { type: Object, required: true },
  demo: Boolean,
})

const robotColors = { R01: overviewRobotColors[0], R02: overviewRobotColors[1], R03: overviewRobotColors[2] }
const rangeByRobot = reactive({ R01: 'Day', R02: 'Day', R03: 'Day' })
const expandedRobotId = ref(null)
const robotList = computed(() => Object.values(props.robots))
const expandedRobot = computed(() => props.robots[expandedRobotId.value] || null)

function realPoints(robotId, range) {
  return selectBatteryHistory(props.history, props.rollingHistory, robotId, range)
}
function pointsFor(robot, range = rangeByRobot[robot.robotId]) {
  const actual = realPoints(robot.robotId, range)
  if (props.demo) return fixedDemoBatteryHistory(robot.robotId, range)
  return actual.length < 2 ? fixedDemoBatteryHistory(robot.robotId, range, actual.at(-1)) : actual
}
function latestFor(robot) {
  return pointsFor(robot).at(-1) || {
    value: robot.battery,
    status: robot.status,
    task: robot.currentTask,
    taskId: robot.taskId,
  }
}
function batteryFor(robot) {
  const value = latestFor(robot).value
  return Number.isFinite(value) ? Math.round(value) : null
}
function statusText(robot) {
  const latest = latestFor(robot)
  return [robotStatusLabels[latest.status || robot.status] || latest.status || robot.status, latest.task || robot.currentTask, latest.taskId || robot.taskId].filter(Boolean).join(' · ') || '尚無最新狀態'
}
function closeExpanded() {
  expandedRobotId.value = null
}
</script>

<template>
  <section class="floor-realtime-panel" :aria-label="`Floor ${floor.slice(-1)} 機器人電量趨勢`">
    <article v-for="(robot, index) in robotList" :key="robot.robotId" class="robot-trend-column" :style="{ '--robot-color': robotColors[robot.robotId], '--robot-index': index }">
      <header class="robot-column-header">
        <strong class="robot-name">{{ robot.name }}</strong>
        <nav class="battery-range-tabs" :aria-label="`${robot.name} 時間範圍`">
          <button v-for="option in batteryRanges" :key="option" type="button" :aria-pressed="rangeByRobot[robot.robotId] === option" @click="rangeByRobot[robot.robotId] = option">{{ option }}</button>
        </nav>
        <strong class="battery-value">{{ batteryFor(robot) === null ? '—' : `${batteryFor(robot)}%` }}</strong>
        <button class="expand-button" type="button" :aria-label="`展開 ${robot.name} 電量趨勢`" @click="expandedRobotId = robot.robotId"><Maximize2 :size="11"/></button>
        <p class="latest-status">{{ statusText(robot) }}</p>
        <div class="battery-segments" role="img" :aria-label="batteryFor(robot) === null ? '無電量資料' : `電量 ${batteryFor(robot)}%`">
          <span v-for="segment in 10" :key="`${robot.robotId}-${batteryFor(robot)}-${segment}`" :class="{ 'is-active': batteryFor(robot) !== null && segment <= Math.round(batteryFor(robot) / 10) }" :style="{ '--segment-index': segment - 1 }"></span>
        </div>
      </header>
      <RobotBatteryTrend :points="pointsFor(robot)" :robot-name="robot.name" :range="rangeByRobot[robot.robotId]" :color="robotColors[robot.robotId]"/>
    </article>

    <Teleport to="body">
    <div v-if="expandedRobot" class="battery-dialog-backdrop" :style="overviewThemeVars" role="presentation" @click.self="closeExpanded">
      <section class="battery-dialog overview-tool-panel" role="dialog" aria-modal="true" :aria-label="`${expandedRobot.name} 大型電量趨勢`" :style="{ '--robot-color': robotColors[expandedRobot.robotId] }" @keydown.esc="closeExpanded">
        <header>
          <div><h2>{{ expandedRobot.name }} 電量趨勢</h2><p>{{ statusText(expandedRobot) }}</p></div>
          <nav class="battery-range-tabs" :aria-label="`${expandedRobot.name} 時間範圍`">
            <button v-for="option in batteryRanges" :key="option" type="button" :aria-pressed="rangeByRobot[expandedRobot.robotId] === option" @click="rangeByRobot[expandedRobot.robotId] = option">{{ option }}</button>
          </nav>
          <strong class="battery-value">{{ batteryFor(expandedRobot) === null ? '—' : `${batteryFor(expandedRobot)}%` }}</strong>
          <button class="dialog-close" type="button" aria-label="關閉大型電量趨勢" autofocus @click="closeExpanded"><X :size="18"/></button>
        </header>
        <RobotBatteryTrend :points="pointsFor(expandedRobot)" :robot-name="expandedRobot.name" :range="rangeByRobot[expandedRobot.robotId]" :color="robotColors[expandedRobot.robotId]" large/>
      </section>
    </div>
    </Teleport>
  </section>
</template>

<style scoped>
.floor-realtime-panel{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));height:100%;min-width:0;min-height:0;padding:16px 18px;box-sizing:border-box;background:transparent}.robot-trend-column{display:grid;grid-template-rows:auto minmax(105px,1fr);min-width:0;min-height:0;padding:0 13px;overflow:hidden;animation:dashboard-fade 280ms ease calc(var(--robot-index)*80ms) both}.robot-trend-column+.robot-trend-column{border-left:1px solid var(--overview-divider)}.robot-column-header{display:grid;grid-template-columns:minmax(58px,1fr) auto auto 22px;grid-template-rows:30px 20px;align-items:center;gap:3px 8px;min-width:0}.robot-name{overflow:hidden;color:var(--text-primary);font-size:12.5px;font-weight:600;text-overflow:ellipsis;white-space:nowrap}.battery-range-tabs{display:flex;align-items:center;gap:2px}.battery-range-tabs button{height:24px;padding:0 6px;color:var(--text-muted);font-size:9.5px;background:transparent;border:0;border-radius:var(--radius-control);cursor:pointer}.battery-range-tabs button[aria-pressed=true]{color:var(--overview-accent-text);background:var(--overview-accent-soft);box-shadow:inset 0 0 0 1px rgba(var(--overview-accent-rgb),.1)}.battery-value{color:var(--robot-color);font-size:18px;font-weight:700;font-variant-numeric:tabular-nums;white-space:nowrap}.expand-button,.dialog-close{display:grid;place-items:center;padding:0;color:var(--text-secondary);background:transparent;border:0;border-radius:var(--radius-control);cursor:pointer}.expand-button{width:22px;height:22px}.expand-button:hover,.dialog-close:hover{color:var(--theme-primary);background:var(--theme-primary-soft)}.latest-status{min-width:0;margin:0;overflow:hidden;color:var(--text-secondary);font-size:9.5px;text-overflow:ellipsis;white-space:nowrap;grid-column:1/3}.battery-segments{display:grid;grid-template-columns:repeat(10,1fr);gap:2px;width:83px;grid-column:3/5;justify-self:end}.battery-segments span{height:6px;background:rgba(122,135,148,.14);border-radius:2px}.battery-segments .is-active{background:var(--robot-color);animation:segment-light 500ms ease-out calc(var(--segment-index)*100ms) both}.battery-dialog-backdrop{position:fixed;z-index:1000;inset:0;display:grid;place-items:center;padding:5vh 5vw;background:rgba(23,33,43,.16);backdrop-filter:blur(4px)}.battery-dialog{display:grid;width:min(1080px,90vw);height:min(650px,84vh);grid-template-rows:auto minmax(360px,1fr);box-sizing:border-box;padding:22px 24px;color:var(--text-primary)}.battery-dialog>header{display:grid;grid-template-columns:minmax(220px,1fr) auto auto 32px;align-items:center;gap:16px;padding-bottom:14px;border-bottom:1px solid var(--overview-divider)}.battery-dialog h2{margin:0;font-size:18px;font-weight:600}.battery-dialog p{margin:5px 0 0;color:var(--text-secondary);font-size:11px}.battery-dialog .battery-range-tabs button{height:29px;padding:0 9px;font-size:11px}.battery-dialog .battery-value{font-size:22px}.dialog-close{width:32px;height:32px}.battery-dialog .robot-battery-trend{margin-top:10px}button:focus-visible,.robot-battery-trend:focus-visible{outline:2px solid var(--robot-color);outline-offset:1px}@keyframes segment-light{from{background:rgba(122,135,148,.14)}to{background:var(--robot-color)}}@media(max-width:1500px){.robot-trend-column{padding:0 8px}.robot-column-header{gap:2px 4px}.battery-range-tabs button{padding:0 3px;font-size:9px}.battery-segments{width:72px}.latest-status{font-size:9px}}@media(prefers-reduced-motion:reduce){.robot-trend-column,.battery-segments .is-active{animation:none}}
.robot-column-header{position:relative;grid-template-columns:minmax(58px,1fr) auto 18px}
.robot-column-header>.robot-name{grid-column:1;grid-row:1}
.robot-column-header>.battery-range-tabs{position:absolute;z-index:1;top:2px;left:50%;transform:translateX(-50%)}
.robot-column-header>.battery-value{grid-column:2;grid-row:1}
.robot-column-header>.expand-button{grid-column:3;grid-row:1;width:18px;height:18px}
.robot-column-header>.latest-status{grid-column:1/2;grid-row:2}
.robot-column-header>.battery-segments{grid-column:2/4;grid-row:2}
.battery-dialog .battery-range-tabs{position:static;transform:none}
.battery-dialog .battery-value{grid-column:auto;grid-row:auto}
button:focus,button:focus-visible{outline:none;box-shadow:none}
</style>
