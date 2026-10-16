<script setup>
import { computed, watch } from 'vue'
import { Zap } from '@lucide/vue'
import { useCountUp } from '@/composables/useCountUp.js'
import { t } from '@/i18n/index.js'

const props = defineProps({ value: { type: Number, default: null }, active: Boolean })
const known = computed(() => Number.isFinite(props.value))
const { displayed, restart } = useCountUp(() => known.value ? Math.max(0, Math.min(100, props.value)) : 0, { duration: 900 })
watch(() => props.active, active => { if (active) restart() }, { immediate: true })
const state = computed(() => !known.value ? 'unknown' : props.value <= 20 ? 'critical' : props.value <= 40 ? 'warning' : 'normal')
</script>
<template>
  <section class="hmi-gauge energy" :class="`is-${state}`" :aria-label="t('robotStatus.battery')">
    <div class="gauge-heading"><span>{{ t('robotStatus.battery') }}</span><Zap :size="18" aria-hidden="true" /></div>
    <div class="metric-arc battery-arc" role="img" :aria-label="known ? t('robotStatus.batteryValue', { value }) : t('robotStatus.batteryUnknown')">
      <div class="battery-liquid" :style="{ height: `${known ? displayed : 0}%` }"></div>
      <div class="battery-reading"><strong>{{ known ? displayed : '—' }}</strong><span v-if="known">%</span></div>
    </div>
  </section>
</template>
