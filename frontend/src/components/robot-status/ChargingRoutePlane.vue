<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { NAVIGATION_ASSETS } from '@/config/sceneAssets.js'
import { shortestVertexPath } from '@/data/demoActiveRoutes.js'
const props = defineProps({ waypoint: String, target: { type: String, default: 'charging_station_1' } })
const graph = ref(null), error = ref('')
const controller = new AbortController()
const route = computed(() => {
  if (!graph.value) return []
  const from = graph.value.namedWaypoints.find(v => v.name === props.waypoint)
  const to = graph.value.namedWaypoints.find(v => v.name === props.target)
  if (!from || !to) return []
  const vertices = new Map(graph.value.vertices.map(v => [v.id, v]))
  return shortestVertexPath(graph.value, from.id, to.id).map(id => vertices.get(id))
})
const bounds = computed(() => {
  if (!route.value.length) return '0 0 100 60'
  const xs = route.value.map(p => p.x), ys = route.value.map(p => p.y)
  return `${Math.min(...xs)-2} ${Math.min(...ys)-2} ${Math.max(...xs)-Math.min(...xs)+4} ${Math.max(...ys)-Math.min(...ys)+4}`
})
onMounted(async () => {
  try {
    const response = await fetch(NAVIGATION_ASSETS.graph0, { signal: controller.signal })
    if (!response.ok) throw new Error('navigation unavailable')
    graph.value = await response.json()
  } catch (reason) { if (reason.name !== 'AbortError') error.value = '導航圖無法載入' }
})
onBeforeUnmount(() => controller.abort())
</script>
<template>
  <figure class="charging-route-plane" aria-label="充電路線預覽，尚未派遣">
    <svg v-if="route.length" :key="`${waypoint}:${target}`" :viewBox="bounds" role="img" aria-label="沿導航圖 Lane 前往充電站">
      <g v-for="(point, index) in route.slice(1)" :key="point.id" :style="{ '--lane-delay': `${index * 130}ms` }">
        <line class="lane-pending" :x1="route[index].x" :y1="route[index].y" :x2="point.x" :y2="point.y"/>
        <line class="lane-reveal" pathLength="1" :x1="route[index].x" :y1="route[index].y" :x2="point.x" :y2="point.y"/>
        <line class="lane-flow" :x1="route[index].x" :y1="route[index].y" :x2="point.x" :y2="point.y"/>
      </g>
      <circle :cx="route[0].x" :cy="route[0].y" r=".35" fill="#4F9F91"/>
      <circle :cx="route.at(-1).x" :cy="route.at(-1).y" r=".5" fill="#8F9692"/>
    </svg>
    <figcaption>{{ error || (graph && !route.length ? '目前位置無可用充電路徑' : '充電路線預覽 · 尚未派遣') }}</figcaption>
  </figure>
</template>
<style scoped>
.charging-route-plane{position:absolute;inset:auto 10% 0;height:25%;margin:0;pointer-events:none;animation:plane-enter .4s ease both}.charging-route-plane svg{width:100%;height:calc(100% - 24px);overflow:visible;transform:perspective(650px) rotateX(35deg)}line{fill:none;stroke-linecap:round;stroke-width:2;vector-effect:non-scaling-stroke}.lane-pending{stroke:rgba(143,150,146,.24)}.lane-reveal{stroke:#4f9f91;stroke-dasharray:1;animation:lane-reveal .35s ease var(--lane-delay) both}.lane-flow{stroke:#bfe7df;stroke-dasharray:8 18;animation:lane-visible .1s ease calc(var(--lane-delay) + .35s) both,charging-route-flow 1.8s linear infinite}figcaption{text-align:center;color:var(--text-muted);font-size:10px}@keyframes plane-enter{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}@keyframes lane-reveal{from{stroke-dashoffset:1}to{stroke-dashoffset:0}}@keyframes lane-visible{from{opacity:0}to{opacity:1}}@keyframes charging-route-flow{to{stroke-dashoffset:-26}}@media(prefers-reduced-motion:reduce){.charging-route-plane,line{animation:none!important}}
</style>
