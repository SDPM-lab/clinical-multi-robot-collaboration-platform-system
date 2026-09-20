<script setup>
defineProps({
  ticks: { type: Array, required: true },
  labels: { type: Array, required: true },
  positionPercent: { type: Function, required: true },
  formatTime: { type: Function, required: true },
})
</script>

<template>
  <div class="timeline-axis">
    <i v-for="tick in ticks" :key="tick.second" class="tick" :class="{ major: tick.major }" :style="{ left: `${positionPercent(tick.second)}%` }"></i>
    <time v-for="label in labels" :key="label.second" :style="{ left: `${positionPercent(label.second)}%` }">{{ formatTime(label.second) }}</time>
  </div>
</template>

<style scoped>
.timeline-axis{position:sticky;z-index:12;top:0;height:32px;background:color-mix(in srgb,var(--panel-bg-strong) 91%,transparent);border-bottom:1px solid var(--glass-divider);backdrop-filter:blur(8px)}
.tick{position:absolute;top:0;bottom:0;width:1px;background:color-mix(in srgb,var(--glass-divider) 38%,transparent);pointer-events:none}.tick.major{background:color-mix(in srgb,var(--glass-divider) 90%,transparent)}
time{position:absolute;top:9px;color:var(--text-muted);font-size:9px;font-variant-numeric:tabular-nums;white-space:nowrap;transform:translateX(4px)}
</style>
