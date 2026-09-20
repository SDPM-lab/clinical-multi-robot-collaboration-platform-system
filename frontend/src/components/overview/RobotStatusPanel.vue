<script setup>
import { computed, ref } from 'vue'
import AnimatedBatteryValue from './AnimatedBatteryValue.vue'
import { Bot } from '@lucide/vue'
import RobotPreviewStrip from '@/components/overview/RobotPreviewStrip.vue'

const props = defineProps({
  robots: { type: Array, default: () => [] },
  data: { type: Array, default: () => [] },
  progressByRobot: { type: Object, default: () => ({}) },
  theme: { type: String, default: 'light' },
})
const previewReady = ref(false)
const displayedRobots = computed(() => (props.robots.length ? props.robots : props.data).slice(0, 3))
const stateLabel = { executing: '執行中', charging: '充電中', idle: '待命', offline: '離線', error: '異常' }
const batteryColor = (battery) => battery >= 60 ? '#ee9b32' : battery >= 30 ? '#d8b73e' : '#d96565'
const stateColor = (state) => ({
  executing: '#f3a12b',
  charging: '#dfbd43',
  idle: '#70a397',
  offline: '#a8aaa6',
  error: '#d86868',
}[state] || '#a8aaa6')
const progressFor = (robot, index) => props.progressByRobot[`robot${String(index + 1).padStart(2, '0')}`]
  || Object.values(props.progressByRobot).find((progress) => progress.robotId === robot.name)
const currentTask = (robot, index) => progressFor(robot, index)?.steps.find((step) => step.status === 'active')?.label || '目前沒有執行中任務'
const robotStyle = (robot, index) => ({
  '--battery-color': batteryColor(robot.battery),
  '--state-color': stateColor(robot.state),
  '--battery-fraction': Math.max(0, Math.min(100, robot.battery)) / 100,
  '--battery-level': `${Math.max(0, Math.min(100, robot.battery))}%`,
  '--robot-delay': `${index * 140}ms`,
})
</script>

<template>
  <section class="robot-status-panel overview-tool-panel dashboard-panel-enter" aria-label="機器人狀態">
    <h2>機器人狀態<small>FLEET STATUS</small></h2>
    <div class="robot-list">
      <article v-for="(robot, index) in displayedRobots" :key="robot.id" :style="robotStyle(robot, index)">
        <div class="model-slot"><RobotPreviewStrip :theme="theme" :count="1" @ready="previewReady = true" /><Bot v-show="!previewReady" :size="27" :stroke-width="1.35" /></div>
        <div class="robot-information">
          <div class="robot-heading"><h3>{{ robot.name }}</h3><strong :class="{ 'is-low': robot.battery < 30 }"><AnimatedBatteryValue :value="robot.battery" :delay="650 + index * 140" />%</strong></div>
          <div class="robot-state"><i></i>{{ stateLabel[robot.state] || robot.state }}<span v-if="robot.battery < 30" class="low-label">低電量</span></div>
          <div class="energy-meter" role="img" :aria-label="`電量 ${robot.battery}%`">
            <span v-for="segment in 5" :key="segment" class="energy-meter__segment" :class="{ 'is-active': segment <= Math.round(Math.max(0, Math.min(100, robot.battery)) / 20) }" :style="{ '--segment-index': segment - 1 }"></span>
          </div>
          <div class="robot-task-line"><span :title="currentTask(robot, index)">{{ currentTask(robot, index) }}</span><small>· 等待任務 {{ robot.queuedTasks ?? 0 }}</small></div>
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped>
.robot-status-panel{--panel-delay:520ms;box-sizing:border-box;display:grid;grid-template-columns:140px minmax(0,1fr);width:100%;min-width:0;min-height:108px;padding:0;color:#47443d;-webkit-backdrop-filter:var(--overview-glass-filter)}
h2{align-self:center;margin:0;padding:0 18px;font-size:13px;font-weight:600;line-height:1.35;white-space:nowrap}h2 small{display:none}
.robot-list{display:grid;min-width:0;grid-template-columns:repeat(3,minmax(0,1fr))}.robot-list article{display:grid;min-width:0;grid-template-columns:48px minmax(0,1fr);align-items:center;column-gap:12px;padding:12px 18px;border-inline-start:1px solid var(--overview-divider)}
.model-slot{position:relative;display:grid;width:44px;height:64px;align-items:end;justify-items:center}.model-slot :deep(.robot-preview-strip){width:44px;height:64px}.model-slot>svg{position:absolute;align-self:center;color:#7c7768}
.robot-information{display:grid;min-width:0;gap:6px;line-height:1.35}.robot-heading{display:flex;align-items:baseline;justify-content:space-between;gap:8px;white-space:nowrap}.robot-heading h3{margin:0;font-size:11.5px;font-weight:550}.robot-heading strong{color:#b17a28;font-size:17px;font-weight:600;font-variant-numeric:tabular-nums}.robot-heading strong.is-low{color:#c45c5c}.robot-state{display:flex;align-items:center;gap:5px;font-size:10px;color:#726d61}.robot-state i{width:5px;height:5px;background:var(--state-color);border-radius:50%}.low-label{color:#b75f5f;font-size:10.5px;margin-left:3px}.robot-task-line{display:flex;min-width:0;gap:4px;white-space:nowrap;font-size:10px;color:#6d685d}.robot-task-line>span{min-width:0;overflow:hidden;text-overflow:ellipsis}.robot-task-line small{flex:none;font-size:10.5px;color:#837d70}
.energy-meter{display:grid;grid-template-columns:repeat(5,14px);gap:3px;width:82px}.energy-meter__segment{height:6px;border-radius:2px;background:rgba(75,72,66,.12)}.energy-meter__segment.is-active{background:var(--battery-color);transform-origin:left;animation:energy-on 240ms ease-out calc(700ms + var(--robot-delay) + var(--segment-index)*120ms) both}
@keyframes energy-on{from{opacity:.2;transform:scaleX(.6)}to{opacity:1;transform:scaleX(1)}}
@media(min-width:900px) and (max-width:1199px){.robot-status-panel{grid-template-columns:100px minmax(0,1fr)}h2{padding:0 10px}.robot-list article{grid-template-columns:38px minmax(0,1fr);padding-inline:8px;column-gap:8px}.model-slot,.model-slot :deep(.robot-preview-strip){width:38px}}
@media(max-width:899px){.robot-status-panel{grid-template-columns:1fr}h2{padding:12px 16px}.robot-list{grid-template-columns:1fr}.robot-list article{border-inline-start:0;border-top:1px solid var(--overview-divider)}}
@media(prefers-reduced-motion:reduce){.energy-meter__segment.is-active{background:var(--battery-color);transform-origin:left;animation:none;background:var(--battery-color)}}
.robot-list article{animation:dashboard-fade 360ms ease calc(600ms + var(--robot-delay)) both}.model-slot{animation:dashboard-fade 480ms ease calc(680ms + var(--robot-delay)) both}.robot-state i{animation:dashboard-fade 240ms ease calc(1300ms + var(--robot-delay)) both}
</style>
