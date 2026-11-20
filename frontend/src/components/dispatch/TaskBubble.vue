<script setup>
import { robotDisplayCode } from '@/config/robotDisplayCode.js'

defineProps({
  task: { type: Object, required: true },
  size: { type: Number, required: true },
  labelMode: { type: String, default: 'code' },
  startTime: { type: String, required: true },
  endTime: { type: String, required: true },
  priorityLabel: { type: String, required: true },
  editing: { type: Boolean, default: false },
  dragging: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  placement: { type: String, default: 'above' },
})

defineEmits(['pointerdown', 'pointermove', 'pointerup', 'pointercancel'])
</script>

<template>
  <button
    type="button"
    class="task-bubble"
    :class="[`status-${task.status}`, `placement-${placement}`, { 'is-editable': editing && !disabled, 'is-dragging': dragging, 'is-disabled': disabled }]"
    :style="{ width: `${size}px`, height: `${size}px` }"
    :aria-label="`${task.id} ${task.title}，${priorityLabel}優先級，${startTime} 到 ${endTime}`"
    @pointerdown.stop="$emit('pointerdown', $event)"
    @pointermove="$emit('pointermove', $event)"
    @pointerup="$emit('pointerup', $event)"
    @pointercancel="$emit('pointercancel', $event)"
  >
    <strong>{{ task.id }}</strong>
    <span v-if="labelMode !== 'code'" class="task-bubble__title">{{ labelMode === 'short' ? `${task.title.slice(0, 2)}…` : task.title }}</span>
    <time v-if="labelMode === 'full'">{{ startTime }}</time>
    <span class="task-tooltip" role="tooltip">
      <b>{{ task.id }}　{{ task.title }}</b>
      <span>{{ task.robotId ? robotDisplayCode(task.robotId) : '尚未指派' }}</span>
      <span>{{ priorityLabel }}優先級</span>
      <span>{{ startTime }} → {{ endTime }}</span>
      <span>預估 {{ Math.round(task.durationSeconds / 60) }} 分鐘</span>
      <span>{{ task.source }} → {{ task.destination }}</span>
      <span>{{ task.status }}</span>
    </span>
  </button>
</template>

<style scoped>
.task-bubble{position:absolute;z-index:6;top:0;left:0;display:grid;align-content:center;justify-items:center;gap:1px;padding:4px;color:var(--bubble-ink,#fff);text-align:center;background:var(--task-main);border:2px solid color-mix(in srgb,var(--task-main) 72%,white);border-radius:50%;box-shadow:0 5px 14px color-mix(in srgb,var(--task-main) 22%,transparent),inset 0 1px 0 rgba(255,255,255,.34);transform:translate(-50%,-50%);cursor:pointer;touch-action:none;transition:filter .15s ease,box-shadow .15s ease,transform .15s ease}
.task-bubble:hover,.task-bubble:focus-visible{z-index:20;filter:saturate(1.08) brightness(1.04);box-shadow:0 8px 20px color-mix(in srgb,var(--task-main) 34%,transparent),0 0 0 3px var(--task-soft);outline:none;transform:translate(-50%,-50%) scale(1.04)}
.task-bubble strong{font-size:10.5px;line-height:1.05;white-space:nowrap}.task-bubble__title,.task-bubble>time{position:absolute;left:50%;max-width:112px;overflow:hidden;color:var(--text-primary);font-size:8.5px;line-height:1.1;text-overflow:ellipsis;white-space:nowrap;transform:translateX(-50%)}.placement-above .task-bubble__title{top:calc(100% + 4px)}.placement-above>time{top:calc(100% + 15px)}.placement-below .task-bubble__title{bottom:calc(100% + 4px)}.placement-below>time{bottom:calc(100% + 15px)}.task-bubble>time{font-size:7.5px;font-variant-numeric:tabular-nums}.task-bubble.status-completed{filter:saturate(.58);opacity:.62}.task-bubble.is-disabled{cursor:pointer}.task-bubble.is-editable{border-style:dashed;cursor:grab}.task-bubble.is-editable:active,.task-bubble.is-dragging{cursor:grabbing}.task-bubble.is-dragging{opacity:.76;box-shadow:0 10px 25px color-mix(in srgb,var(--task-main) 42%,transparent);transform:translate(-50%,-50%) scale(1.06)}
.task-tooltip{position:absolute;z-index:50;bottom:calc(100% + 9px);left:50%;display:none;width:226px;gap:2px;padding:10px 11px;color:var(--text-secondary);font-size:10.5px;line-height:1.45;text-align:left;background:var(--popover-bg);border:1px solid var(--panel-border);border-radius:7px;box-shadow:var(--dropdown-shadow);pointer-events:none;transform:translateX(-50%)}.placement-above .task-tooltip{top:calc(100% + 9px);bottom:auto}.task-tooltip b{color:var(--text-primary);font-size:11.5px}.task-bubble:hover .task-tooltip,.task-bubble:focus-visible .task-tooltip{display:grid}
@media(prefers-reduced-motion:reduce){.task-bubble{transition:none}}
</style>
