<script setup>
import { computed } from 'vue'
import { clinicFloorOptions } from '@/data/clinicOverviewData.js'

const props = defineProps({
  modelValue: { type: [String, Number], default: 'all' },
  anchors: { type: Object, default: () => ({}) },
  availableFloors: { type: Array, default: () => clinicFloorOptions },
  showAll: { type: Boolean, default: true },
  inline: Boolean,
})
const emit = defineEmits(['update:modelValue'])
const floors = computed(() => props.availableFloors.filter((floor) => floor.id !== 'all').sort((a, b) => a.id - b.id))
const floorTop = { 1: 96, 2: 96, 3: 96 }
const floorLeft = { 1: 108, 2: 180, 3: 252 }
const buttonWidth = 68
const activeLeaderLine = computed(() => {
  if (props.modelValue === 'all') return null
  const anchor = props.anchors[String(props.modelValue)]
  if (!anchor?.visible) return null
  const startX = (floorLeft[props.modelValue] ?? 22) + buttonWidth
  const startY = (floorTop[props.modelValue] ?? 96) + 17
  return { id: props.modelValue, startX, startY, endX: anchor.x, endY: anchor.y }
})
</script>

<template>
  <nav class="clinic-floor-selector" :class="{ inline }" aria-label="診所樓層選擇">
    <svg v-if="activeLeaderLine" aria-hidden="true">
      <g class="is-active"><line class="floor-leader-line" :x1="activeLeaderLine.startX" :y1="activeLeaderLine.startY" :x2="activeLeaderLine.endX" :y2="activeLeaderLine.endY" /></g>
    </svg>
    <button v-if="showAll" class="all-floor" type="button" :class="{ 'is-active': modelValue === 'all' }" :aria-pressed="modelValue === 'all'" @click="emit('update:modelValue', 'all')"><small>ALL</small><span>全棟</span></button>
    <button v-for="floor in floors" :key="floor.id" class="floor-label" type="button" :class="{ 'is-active': modelValue === floor.id }" :style="{ top: `${floorTop[floor.id]}px`, left: `${floorLeft[floor.id]}px` }" :aria-pressed="modelValue === floor.id" @click="emit('update:modelValue', floor.id)"><span>{{ floor.label }}</span></button>
  </nav>
</template>

<style scoped>
.clinic-floor-selector{position:absolute;inset:0;pointer-events:none}.clinic-floor-selector svg{position:absolute;inset:0;width:100%;height:100%;overflow:visible;pointer-events:none}.floor-leader-line{stroke:rgba(var(--color-primary-rgb),.48);stroke-width:1;stroke-dasharray:3 7;pointer-events:none}
button{position:absolute;display:flex;flex-direction:column;align-items:center;justify-content:center;height:34px;padding:0 8px;color:var(--text-secondary);font-size:10px;text-align:center;background:rgba(255,255,255,.48);border:1px solid var(--glass-border);border-radius:4px;box-shadow:var(--info-shadow);backdrop-filter:var(--control-backdrop);pointer-events:auto;cursor:pointer;transition:color 180ms ease,background 220ms ease,border-color 220ms ease,box-shadow 220ms ease;animation:dashboard-panel-enter 520ms cubic-bezier(.22,.8,.3,1) 220ms both}.all-floor{top:96px;left:22px;width:80px;flex-direction:row;gap:6px}.floor-label{width:68px}
button:hover,button.is-active{color:var(--theme-primary);background:var(--theme-primary-soft);border-color:rgba(var(--color-primary-rgb),.3);box-shadow:var(--info-shadow)}button.is-active{background:var(--theme-primary-soft)}small{font-size:9.5px;font-weight:550;line-height:1.2}span{font-weight:550;font-size:9.5px;line-height:1.2}.all-floor small{font-size:10px}.all-floor span{font-size:11px}button:focus-visible{outline:2px solid rgba(var(--color-primary-rgb),.42);outline-offset:2px}
.inline{position:relative;inset:auto;display:flex;gap:6px;width:max-content}.inline button{position:relative;top:auto!important;left:auto!important;animation:none}.inline svg{display:none}
</style>
