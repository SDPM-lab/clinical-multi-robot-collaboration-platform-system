<script setup>
import { computed } from 'vue'
import { clinicFloorOptions } from '@/data/clinicOverviewData.js'

const props = defineProps({
  modelValue: { type: [String, Number], default: 'all' },
  anchors: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['update:modelValue'])
const floors = clinicFloorOptions.filter((floor) => floor.id !== 'all')
const floorTop = { 3: 346, 2: 346, 1: 390 }
const floorLeft = { 3: 22, 2: 88, 1: 22 }
const buttonWidth = 60
const activeLeaderLine = computed(() => {
  if (props.modelValue === 'all') return null
  const anchor = props.anchors[String(props.modelValue)]
  if (!anchor?.visible) return null
  const startX = (floorLeft[props.modelValue] ?? 22) + buttonWidth
  const startY = (floorTop[props.modelValue] ?? 346) + 17
  return { id: props.modelValue, startX, startY, endX: anchor.x, endY: anchor.y }
})
</script>

<template>
  <nav class="clinic-floor-selector" aria-label="診所樓層選擇">
    <svg v-if="activeLeaderLine" aria-hidden="true">
      <g class="is-active"><line class="floor-leader-line" :x1="activeLeaderLine.startX" :y1="activeLeaderLine.startY" :x2="activeLeaderLine.endX" :y2="activeLeaderLine.endY" /></g>
    </svg>
    <button class="all-floor" type="button" :class="{ 'is-active': modelValue === 'all' }" :aria-pressed="modelValue === 'all'" @click="emit('update:modelValue', 'all')"><small>ALL</small><span>全棟</span></button>
    <button v-for="floor in floors" :key="floor.id" class="floor-label" type="button" :class="{ 'is-active': modelValue === floor.id }" :style="{ top: `${floorTop[floor.id]}px`, left: `${floorLeft[floor.id]}px` }" :aria-pressed="modelValue === floor.id" @click="emit('update:modelValue', floor.id)"><span>{{ floor.label }}</span></button>
  </nav>
</template>

<style scoped>
.clinic-floor-selector{position:absolute;inset:0;pointer-events:none}.clinic-floor-selector svg{position:absolute;inset:0;width:100%;height:100%;overflow:visible;pointer-events:none}.floor-leader-line{stroke:rgba(213,111,40,.44);stroke-width:1;stroke-dasharray:3 7;pointer-events:none}
button{position:absolute;display:flex;flex-direction:column;align-items:center;justify-content:center;height:34px;padding:0 6px;color:rgba(40,43,42,.76);font-size:10px;text-align:center;background:rgba(248,249,248,.52);border:1px solid rgba(255,255,255,.56);border-radius:var(--control-radius);pointer-events:auto;cursor:pointer;transition:color 180ms ease,background 220ms ease,border-color 220ms ease,box-shadow 220ms ease;animation:dashboard-panel-enter 520ms cubic-bezier(.22,.8,.3,1) 220ms both}.all-floor{top:302px;left:22px;width:126px;flex-direction:row;gap:6px}.floor-label{width:60px}
button:hover,button.is-active{color:#ad531b;background:linear-gradient(100deg,rgba(255,127,35,.18),rgba(255,191,70,.10),rgba(255,255,255,.34));border-color:rgba(225,120,41,.30);box-shadow:0 6px 17px rgba(225,126,47,.08)}button.is-active{background:linear-gradient(100deg,rgba(255,127,35,.23),rgba(255,191,70,.14),rgba(255,255,255,.34))}small{font-size:9.5px;font-weight:550;line-height:1.2}span{font-weight:550;font-size:9.5px;line-height:1.2}.all-floor small{font-size:10px}.all-floor span{font-size:11px}button:focus-visible{outline:2px solid rgba(213,111,40,.44);outline-offset:2px}
</style>
