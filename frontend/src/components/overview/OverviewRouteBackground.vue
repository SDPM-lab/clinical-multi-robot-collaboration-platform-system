<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { NAVIGATION_ASSETS } from '@/config/sceneAssets.js'

defineProps({ entrance: Boolean })
const graph = ref(null)
const error = ref('')
const isPageHidden = ref(false)
const vertices = computed(() => new Map((graph.value?.vertices || []).map((vertex) => [vertex.id, vertex])))
const lanes = computed(() => {
  const seen = new Set()
  return (graph.value?.lanes || []).filter((lane) => {
    const key = [lane.from, lane.to].sort().join(':')
    if (seen.has(key) || !vertices.value.has(lane.from) || !vertices.value.has(lane.to)) return false
    seen.add(key)
    return true
  })
})
const bounds = computed(() => {
  const values = [...vertices.value.values()]
  if (!values.length) return { x: 0, y: 0, width: 100, height: 60 }
  const xs = values.map(({ x }) => x)
  const ys = values.map(({ y }) => y)
  const padding = 2.4
  const minX = Math.min(...xs) - padding
  const minY = Math.min(...ys) - padding
  return { x: minX, y: minY, width: Math.max(...xs) - minX + padding, height: Math.max(...ys) - minY + padding }
})
const viewBox = computed(() => `${bounds.value.x} ${bounds.value.y} ${bounds.value.width} ${bounds.value.height}`)
const nodeIds = computed(() => {
  const degree = new Map()
  lanes.value.forEach((lane) => {
    degree.set(lane.from, (degree.get(lane.from) || 0) + 1)
    degree.set(lane.to, (degree.get(lane.to) || 0) + 1)
  })
  return new Set([...vertices.value.values()].filter((vertex) => vertex.name || degree.get(vertex.id) !== 2).map(({ id }) => id))
})

// Six junctions span the route map; two teal nodes keep the accent ratio near 70/30.
const signalNodeConfig = Object.freeze([
  { id: 'v19', delay: '0s', secondary: false },
  { id: 'v16', delay: '1.35s', secondary: true },
  { id: 'v14', delay: '2.7s', secondary: false },
  { id: 'v11', delay: '4.05s', secondary: false },
  { id: 'v1', delay: '5.4s', secondary: true },
  { id: 'v0', delay: '6.75s', secondary: false },
])
const signalNodes = computed(() => signalNodeConfig.map((item) => ({ ...item, vertex: vertices.value.get(item.id) })).filter(({ vertex }) => vertex))
const signalLanes = computed(() => lanes.value.filter((_, index) => index % 4 === 1))
const isSecondaryLane = (lane) => signalNodeConfig.some(({ id, secondary }) => secondary && (lane.from === id || lane.to === id))
const updateVisibility = () => { isPageHidden.value = document.hidden }

onMounted(async () => {
  document.addEventListener('visibilitychange', updateVisibility)
  updateVisibility()
  try {
    const response = await fetch(NAVIGATION_ASSETS.graph0, { cache: 'no-store' })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    graph.value = await response.json()
  } catch (reason) {
    error.value = `Graph 0 背景載入失敗：${reason instanceof Error ? reason.message : reason}`
  }
})
onBeforeUnmount(() => document.removeEventListener('visibilitychange', updateVisibility))
</script>

<template>
  <div class="overview-route-background" :class="{ 'is-paused': isPageHidden, 'is-entering': entrance }" aria-hidden="true">
    <svg v-if="graph" :viewBox="viewBox" preserveAspectRatio="xMidYMid meet">
      <defs>
        <filter id="circuit-soft-glow" x="-250%" y="-250%" width="600%" height="600%"><feGaussianBlur stdDeviation="0.48" /></filter>
        <filter id="circuit-wave-soften" x="-80%" y="-80%" width="260%" height="260%"><feGaussianBlur stdDeviation="0.055" /></filter>
      </defs>
      <g class="graph-network-underlay">
        <line v-for="lane in lanes" :key="`underlay-${lane.id}`" class="graph-lane graph-lane--underlay" pathLength="1" :x1="vertices.get(lane.from).x" :y1="vertices.get(lane.from).y" :x2="vertices.get(lane.to).x" :y2="vertices.get(lane.to).y" />
      </g>
      <g class="graph-network-main">
        <line v-for="lane in lanes" :key="lane.id" class="graph-lane" pathLength="1" :x1="vertices.get(lane.from).x" :y1="vertices.get(lane.from).y" :x2="vertices.get(lane.to).x" :y2="vertices.get(lane.to).y" />
        <line v-for="(lane, index) in signalLanes" :key="`signal-${lane.id}`" class="circuit-line--signal" :class="{ 'is-secondary': isSecondaryLane(lane) }" :style="{ '--line-delay': `${-index * 0.72}s` }" :x1="vertices.get(lane.from).x" :y1="vertices.get(lane.from).y" :x2="vertices.get(lane.to).x" :y2="vertices.get(lane.to).y" />
        <circle v-for="vertex in graph.vertices" :key="`minor-${vertex.id}`" class="graph-node graph-node--minor" :cx="vertex.x" :cy="vertex.y" r="0.07" />
        <circle v-for="vertex in graph.vertices.filter((entry) => nodeIds.has(entry.id))" :key="`major-${vertex.id}`" class="graph-node graph-node--major" :cx="vertex.x" :cy="vertex.y" r="0.13" />
      </g>
      <g v-for="node in signalNodes" :key="`pulse-${node.id}`" class="circuit-signal-node" :class="{ 'is-secondary': node.secondary }" :style="{ '--node-delay': node.delay }">
        <circle class="circuit-node-glow" :cx="node.vertex.x" :cy="node.vertex.y" r="1.15" />
        <circle class="circuit-wave circuit-wave--1" :cx="node.vertex.x" :cy="node.vertex.y" r="0.5" />
        <circle class="circuit-wave circuit-wave--2" :cx="node.vertex.x" :cy="node.vertex.y" r="0.5" />
        <circle class="circuit-wave circuit-wave--3" :cx="node.vertex.x" :cy="node.vertex.y" r="0.5" />
        <circle class="entrance-wave" :cx="node.vertex.x" :cy="node.vertex.y" r=".5" />
        <circle class="circuit-node-core" :cx="node.vertex.x" :cy="node.vertex.y" r="0.18" />
      </g>
    </svg>
    <p v-else-if="error">{{ error }}</p>
  </div>
</template>

<style scoped>
.overview-route-background{position:absolute;z-index:1;top:78px;right:0;bottom:0;left:0;overflow:hidden;background:transparent;pointer-events:none}
svg{display:block;box-sizing:border-box;width:116%;height:100%;margin-left:-8%;padding:42px 0 8px;overflow:visible;opacity:.78;background:transparent;transform:translateY(-9%) scaleX(1.72) scaleY(1.5);transform-origin:center center}
.graph-lane{fill:none;stroke:var(--circuit-line);stroke-width:1.05;vector-effect:non-scaling-stroke}.graph-lane--underlay{stroke:var(--circuit-line-underlay);stroke-width:5}
.graph-node{fill:var(--circuit-node)}.graph-node--minor{opacity:.58}.graph-node--major{opacity:.9}
.circuit-signal-node{--wave-peak:.14;color:var(--circuit-signal)}.circuit-signal-node.is-secondary{color:var(--circuit-secondary-signal)}
.circuit-node-glow{fill:currentColor;filter:url(#circuit-soft-glow);opacity:.08;transform-box:fill-box;transform-origin:center;animation:circuit-node-breathe 10.8s ease-in-out var(--node-delay) infinite}
.circuit-node-core{fill:currentColor;opacity:.3;transform-box:fill-box;transform-origin:center;animation:circuit-node-breathe 10.8s ease-in-out var(--node-delay) infinite}
.circuit-wave{fill:none;stroke:currentColor;stroke-width:.045;filter:url(#circuit-wave-soften);opacity:0;transform-box:fill-box;transform-origin:center;animation:circuit-wave-pulse 10.8s ease-out var(--node-delay) infinite}
.circuit-wave--2{animation-delay:calc(var(--node-delay) + .72s)}.circuit-wave--3{animation-delay:calc(var(--node-delay) + 1.44s)}
.circuit-line--signal{fill:none;color:var(--circuit-signal);stroke:currentColor;stroke-width:1.45;stroke-linecap:round;stroke-dasharray:3 42;opacity:.32;vector-effect:non-scaling-stroke;animation:circuit-signal-flow 9.6s linear var(--line-delay) infinite}.circuit-line--signal.is-secondary{color:var(--circuit-secondary-signal);opacity:.27}
.is-paused .circuit-wave,.is-paused .circuit-line--signal,.is-paused .circuit-node-glow,.is-paused .circuit-node-core{animation-play-state:paused}
p{position:absolute;inset:0;display:grid;place-items:center;color:var(--text-muted);font-size:12px}
@keyframes circuit-wave-pulse{0%,4%{opacity:0;transform:scale(.3)}10%{opacity:var(--wave-peak)}38%{opacity:.045}52%,100%{opacity:0;transform:scale(5)}}
@keyframes circuit-node-breathe{0%,5%,34%,100%{opacity:.07;transform:scale(.78)}12%{opacity:.31;transform:scale(1.2)}25%{opacity:.11;transform:scale(1)}}
@keyframes circuit-signal-flow{from{stroke-dashoffset:0}to{stroke-dashoffset:-180}}
[data-theme='dark'] .overview-route-background svg{opacity:.54}[data-theme='dark'] .circuit-signal-node{--wave-peak:.19}[data-theme='dark'] .circuit-line--signal{opacity:.36}[data-theme='dark'] .circuit-line--signal.is-secondary{opacity:.3}
@media(prefers-reduced-motion:reduce){.circuit-wave,.circuit-line--signal,.circuit-node-glow,.circuit-node-core{animation:none}.circuit-wave{display:none}.circuit-node-glow{opacity:.12}.circuit-node-core{opacity:.4}}
.is-entering .graph-lane{stroke-dasharray:1;animation:overview-circuit-draw .5s ease-out both}
.is-entering .graph-node{animation:overview-node-enter .6s ease-out .25s both}
.entrance-wave{display:none;fill:none;stroke:currentColor;stroke-width:.055;transform-box:fill-box;transform-origin:center}
.is-entering .entrance-wave{display:block;animation:overview-node-wave .6s ease-out .25s both}
@keyframes overview-circuit-draw{from{stroke-dashoffset:1;opacity:0}to{stroke-dashoffset:0;opacity:1}}
@keyframes overview-node-enter{from{opacity:0}to{opacity:1}}
@keyframes overview-node-wave{from{opacity:0;transform:scale(1)}30%{opacity:.4}to{opacity:0;transform:scale(5)}}
@media(prefers-reduced-motion:reduce){.is-entering .graph-lane,.is-entering .graph-node{animation:none}.is-entering .entrance-wave{display:none}}
</style>
