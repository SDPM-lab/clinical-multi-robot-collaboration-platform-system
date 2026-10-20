<script setup>
import { computed, watch } from 'vue'
import { Thermometer } from '@lucide/vue'
import { useCountUp } from '@/composables/useCountUp.js'
import { thermalState } from '@/config/robotHmi.js'
import { t } from '@/i18n/index.js'

const props = defineProps({ value: { type: Number, default: null }, active: Boolean })
const { displayed, restart } = useCountUp(() => props.value, { duration: 900 })
const state = computed(() => thermalState(props.value))
const progress = computed(() => Number.isFinite(props.value) ? Math.max(0, Math.min(100, displayed.value)) : 0)
const indicator = computed(() => {
  const angle = (135 + progress.value * 2.7) * Math.PI / 180
  return { x: 80 + 68 * Math.cos(angle), y: 80 + 68 * Math.sin(angle) }
})
const statusText = computed(() => t(state.value === 'critical' ? 'robotStatus.temperatureCritical' : state.value === 'warning' ? 'robotStatus.temperatureWarning' : state.value === 'unknown' ? 'robotStatus.temperatureUnknown' : 'robotStatus.temperatureNormal'))
watch(() => props.active, active => { if (active) restart() }, { immediate: true })
</script>
<template>
  <section class="hmi-gauge thermal" :class="`is-${state}`" :aria-label="t('robotStatus.temperature')">
    <div class="gauge-heading"><span>{{ t('robotStatus.temperature') }}</span><Thermometer :size="18" aria-hidden="true" /></div>
    <div class="thermal-visual" role="img" :aria-label="state === 'unknown' ? statusText : `${t('robotStatus.temperatureValue', { value })} · ${statusText}`">
      <div class="thermal-dial">
        <svg class="thermal-dial__scale" viewBox="0 0 160 160" aria-hidden="true">
          <defs><linearGradient id="thermal-scale-gradient"><stop offset="0%" stop-color="#A8DDEB"/><stop offset="38%" stop-color="#EAB7CF"/><stop offset="68%" stop-color="#ED7C84"/><stop offset="100%" stop-color="#F03B38"/></linearGradient></defs>
          <path class="thermal-dial__track" d="M 32 128 A 68 68 0 1 1 128 128"/>
          <path class="thermal-dial__arc" d="M 32 128 A 68 68 0 1 1 128 128"/>
          <circle v-if="state !== 'unknown'" class="thermal-dial__indicator" :cx="indicator.x" :cy="indicator.y" r="5"/>
        </svg>
        <strong class="thermal-reading">{{ state === 'unknown' ? '—' : displayed }}<em v-if="state !== 'unknown'">°C</em></strong>
      </div>
    </div>
  </section>
</template>
