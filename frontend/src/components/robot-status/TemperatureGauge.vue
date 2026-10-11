<script setup>
import { computed, watch } from 'vue'
import { TriangleAlert, Thermometer } from '@lucide/vue'
import { useCountUp } from '@/composables/useCountUp.js'
import { thermalState } from '@/config/robotHmi.js'

const props = defineProps({ value: { type: Number, default: null }, active: Boolean })
const { displayed, restart } = useCountUp(() => props.value, { duration: 900 })
const state = computed(() => thermalState(props.value))
const progress = computed(() => Number.isFinite(props.value) ? Math.max(0, Math.min(100, displayed.value)) : 0)
watch(() => props.active, active => { if (active) restart() }, { immediate: true })
</script>
<template>
  <section class="hmi-gauge thermal" :class="`is-${state}`" aria-label="溫度儀表">
    <div class="gauge-heading"><span>Temperature</span><Thermometer :size="18" aria-hidden="true" /></div>
    <div class="thermal-visual" role="img" :aria-label="state === 'unknown' ? '溫度尚未提供' : `溫度 ${value} 度`">
      <div class="thermal-track"><div class="thermal-fill" :style="{ height: `${progress}%` }"></div><span class="thermal-mark" :style="{ bottom: `${progress}%` }"></span></div>
      <strong class="thermal-reading">{{ state === 'unknown' ? '—' : displayed }}<em v-if="state !== 'unknown'">°C</em></strong>
    </div>
    <p v-if="state === 'critical'" role="alert"><TriangleAlert :size="13"/>馬達溫度過高</p>
    <p v-else>{{ state === 'warning' ? '溫度偏高' : state === 'unknown' ? '尚無溫度資料' : '溫度正常' }}</p>
  </section>
</template>
