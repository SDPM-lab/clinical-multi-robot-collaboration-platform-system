<script setup>
import { computed, onMounted } from 'vue'
import { useCountUp } from '@/composables/useCountUp.js'
const props = defineProps({ robots: { type: Array, default: null } })
const known = computed(() => Array.isArray(props.robots) && props.robots.every(robot => ['connected', 'connecting', 'disconnected'].includes(robot.connectionState)))
const connected = computed(() => known.value ? props.robots.filter(robot => robot.connectionState === 'connected').length : null)
const { displayed, restart } = useCountUp(() => connected.value, { duration: 500 })
onMounted(restart)
</script>
<template>
  <section class="connectivity-panel overview-tool-panel" aria-label="機器人連線">
    <h2>機器人連線</h2>
    <div class="connection-count" :aria-label="known ? `${connected} / ${robots.length}` : 'Unavailable'"><strong>{{ known ? displayed : '—' }}</strong><span v-if="robots">/ {{ robots.length }}</span></div>
    <p aria-live="polite">{{ known ? 'robots connected' : 'Unavailable' }}</p>
  </section>
</template>
<style scoped>
.connectivity-panel{display:grid;grid-template-rows:auto minmax(0,1fr) auto;align-items:center;justify-items:center;min-height:0;padding:12px 14px;gap:6px}h2{justify-self:start;margin:0;font-size:13px;font-weight:500}.connection-count{display:flex;align-items:baseline;gap:8px;font-variant-numeric:tabular-nums}.connection-count strong{color:var(--theme-primary);font-size:clamp(25px,3vw,38px);font-weight:400}.connection-count span{color:var(--text-secondary);font-size:20px;font-weight:400}p{margin:0;font-size:11px;color:var(--text-secondary)}
h2{display:flex;align-items:center;gap:7px}h2 svg{flex:none;color:var(--theme-primary)}
</style>
