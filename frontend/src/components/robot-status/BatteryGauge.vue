<script setup>
import { computed, watch } from 'vue'
import { Zap } from '@lucide/vue'
import { useCountUp } from '@/composables/useCountUp.js'

const props = defineProps({ value: { type: Number, default: null }, charging: Boolean, runtime: String, active: Boolean, status: { type: String, default: null } })
const known = computed(() => Number.isFinite(props.value))
const { displayed, restart } = useCountUp(() => known.value ? Math.max(0, Math.min(100, props.value)) : 0, { duration: 900 })
watch(() => props.active, active => { if (active) restart() }, { immediate: true })
const state = computed(() => !known.value ? 'unknown' : props.value <= 20 ? 'critical' : props.value <= 40 ? 'warning' : 'normal')
const statusLabel = computed(() => props.charging ? '充電中' : props.status === 'Idle' ? '待命中' : '電量狀態')
</script>
<template>
  <section class="hmi-gauge energy" :class="`is-${state}`" aria-label="電量儀表">
    <div class="gauge-heading"><span>Battery</span><Zap :size="18" aria-hidden="true" /></div>
    <div class="metric-arc battery-arc" role="img" :aria-label="known ? `電量 ${value}%` : '電量尚未提供'">
      <div class="battery-liquid" :style="{ height: `${known ? displayed : 0}%` }"></div>
      <div class="battery-reading"><strong>{{ known ? displayed : '—' }}</strong><span v-if="known">%</span></div>
    </div>
    <p>{{ statusLabel }}<span v-if="runtime"> · {{ runtime }}</span></p>
  </section>
</template>
