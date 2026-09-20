<script setup>
import { computed, onMounted, ref } from 'vue'
import { rmfToThree } from '@/config/rmfMapTransform.js'
import { locationDetails } from '@/data/demoActiveRoutes.js'
import { NAVIGATION_ASSETS } from '@/config/sceneAssets.js'
import { getRobotVisualTheme } from '@/config/robotVisualThemes.js'
import { historyStatusColors } from '@/data/historyPresentation.js'
import { t, translateLocation } from '@/i18n/index.js'

const props = defineProps({
  robots: { type: Array, required: true },
  destination: { type: String, default: '' },
  origin: { type: String, default: '' },
  robotId: { type: String, default: 'R01' },
  compact: { type: Boolean, default: false },
  readOnly: { type: Boolean, default: false },
  routeCoordinates: { type: Array, default: () => [] },
  routeProgress: { type: Number, default: 0.5 },
  historical: { type: Boolean, default: false },
  historyStatus: { type: String, default: '' },
})
const emit = defineEmits(['select-destination'])
const data = ref(null)
const selected = ref(null)
const zoom = ref(1)
const pan = ref({ x: 0, y: 0 })
const drag = ref(null)
onMounted(async () => { try { data.value = await fetch(NAVIGATION_ASSETS.graph0, { cache: 'no-store' }).then((response) => response.json()) } catch { data.value = {vertices:[],lanes:[],namedWaypoints:[]} } })
const vertices = computed(() => new Map((data.value?.vertices || []).map((vertex) => [vertex.id, { ...vertex, world: rmfToThree(vertex) }])))
const mapPoint = (vertex) => ({ x: (vertex.world.x + 20) * 22, y: (vertex.world.z + 14) * 22 })
const locations = computed(() => (data.value?.namedWaypoints || []).filter((waypoint) => locationDetails[waypoint.name]).map((waypoint) => ({ ...waypoint, ...locationDetails[waypoint.name], world: rmfToThree(waypoint) })))
const laneLines = computed(() => (data.value?.lanes || []).filter((lane, index) => index % 2 === 0).map((lane) => ({ id: lane.id, a: mapPoint(vertices.value.get(lane.from)), b: mapPoint(vertices.value.get(lane.to)) })))
const namedByLabel = computed(() => new Map(locations.value.map((location) => [location.label, location])))
const mainEntrance = computed(() => {
  const door = data.value?.doors?.find((entry) => entry.name === 'main_entrance')
  if (!door?.endpoints?.length) return null
  const rmf = {
    x: door.endpoints.reduce((sum, point) => sum + point[0], 0) / door.endpoints.length,
    y: door.endpoints.reduce((sum, point) => sum + point[1], 0) / door.endpoints.length,
  }
  return { id: 'door-main-entrance', label: 'Main Entrance', world: rmfToThree(rmf) }
})
const robotPoints = computed(() => props.robots.map((robot) => ({
  ...robot,
  location: namedByLabel.value.get(robot.currentLocation)
    || (robot.currentLocation === 'Main Entrance' ? mainEntrance.value : null),
})).filter((robot) => robot.location))
const routePoints = computed(() => {
  if (props.compact && props.routeCoordinates.length) return props.routeCoordinates.map(([x,y])=>({x,y}))
  const start = namedByLabel.value.get(props.origin)
  const destination = namedByLabel.value.get(props.destination)
  if (!start || !destination || !data.value) return props.routeCoordinates.map(([x,y])=>({x,y}))
  const adjacency = new Map()
  data.value.lanes.forEach((lane) => { if (!adjacency.has(lane.from)) adjacency.set(lane.from, []); adjacency.get(lane.from).push(lane.to) })
  const queue = [[start.id]]; const seen = new Set([start.id])
  while (queue.length) {
    const path = queue.shift(); const tail = path.at(-1)
    if (tail === destination.id) return path.map((id) => mapPoint(vertices.value.get(id)))
    for (const next of adjacency.get(tail) || []) if (!seen.has(next)) { seen.add(next); queue.push([...path, next]) }
  }
  return props.routeCoordinates.map(([x,y])=>({x,y}))
})
const compactRobotPoint = computed(() => {
  const points=routePoints.value
  if (!points.length) return null
  if (props.historical) return {x:points.at(-1).x+20,y:points.at(-1).y+18}
  const position=Math.min(points.length-1,Math.max(0,Math.round((points.length-1)*props.routeProgress)))
  return points[position]
})
const compactViewBox = computed(() => {
  const points=routePoints.value
  if (!points.length) return '105 125 640 360'
  const xs=points.map(point=>point.x),ys=points.map(point=>point.y)
  const centerX=(Math.min(...xs)+Math.max(...xs))/2,centerY=(Math.min(...ys)+Math.max(...ys))/2
  let width=Math.max(250,Math.max(...xs)-Math.min(...xs)+150)
  let height=Math.max(130,Math.max(...ys)-Math.min(...ys)+110)
  if(width/height<2.45)width=height*2.45
  else height=width/2.45
  return `${centerX-width/2} ${centerY-height/2} ${width} ${height}`
})
const transform = computed(() => `translate(${pan.value.x} ${pan.value.y}) scale(${zoom.value})`)
const selectedTheme = computed(() => getRobotVisualTheme(props.robotId))
const mapThemeStyle = computed(() => ({ '--route-color': selectedTheme.value.main, '--route-soft': selectedTheme.value.soft, '--history-status-color':historyStatusColors[props.historyStatus]||'var(--theme-primary)' }))
const changeZoom = (factor) => { zoom.value = Math.max(.65, Math.min(2.6, zoom.value * factor)) }
const resetView = () => { zoom.value = 1; pan.value = { x: 0, y: 0 } }
const onWheel = (event) => { event.preventDefault(); event.stopPropagation(); changeZoom(event.deltaY > 0 ? .9 : 1.1) }
const onPointerDown = (event) => { drag.value = { x: event.clientX, y: event.clientY, panX: pan.value.x, panY: pan.value.y }; event.currentTarget.setPointerCapture(event.pointerId) }
const onPointerMove = (event) => { if (drag.value) pan.value = { x: drag.value.panX + event.clientX - drag.value.x, y: drag.value.panY + event.clientY - drag.value.y } }
const onPointerUp = () => { drag.value = null }
</script>

<template>
  <section class="mini-map" :class="{'is-compact':compact,'is-historical':historical}" :style="mapThemeStyle" :aria-label="t('map.title')">
    <div v-if="!compact" class="map-title"><strong>{{t('map.title')}}</strong><span>點擊 Marker 選擇目的地</span></div>
    <div class="map-controls"><button type="button" :aria-label="t('map.zoomIn')" @click="changeZoom(1.15)">＋</button><button type="button" :aria-label="t('map.zoomOut')" @click="changeZoom(.87)">－</button><button v-if="!compact" type="button" @click="resetView">{{t('map.reset')}}</button></div>
    <div class="map-stage">
      <svg v-if="data" :viewBox="compact?compactViewBox:'0 0 850 600'" @wheel="onWheel" @pointerdown="onPointerDown" @pointermove="onPointerMove" @pointerup="onPointerUp" @pointercancel="onPointerUp">
        <defs><marker id="history-route-arrow" markerWidth="8" markerHeight="8" refX="5" refY="4" orient="auto" markerUnits="strokeWidth"><path d="M1 1 L6 4 L1 7" fill="none" stroke="#a75527" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></marker></defs>
        <g :transform="transform">
          <rect x="0" y="0" width="850" height="600" class="building-footprint" />
          <line v-for="lane in laneLines" :key="lane.id" :x1="lane.a.x" :y1="lane.a.y" :x2="lane.b.x" :y2="lane.b.y" class="map-lane" />
          <polyline v-if="routePoints.length" pathLength="1" :points="routePoints.map((point) => `${point.x},${point.y}`).join(' ')" class="estimate-route" :class="{'compact-route':compact&&!historical}" :marker-mid="compact&&!historical?'url(#history-route-arrow)':undefined" />
          <g v-if="compact && routePoints.length" class="compact-endpoint" :transform="`translate(${routePoints[0].x} ${routePoints[0].y})`"><circle r="9"/><text y="-16">{{translateLocation(origin)}}</text></g>
          <g v-if="compact && routePoints.length" class="compact-endpoint is-destination" :transform="`translate(${routePoints.at(-1).x} ${routePoints.at(-1).y})`"><circle r="9"/><text v-if="historical" class="endpoint-state" y="5">{{historyStatus==='completed'?'✓':historyStatus==='cancelled'?'×':historyStatus==='failed'?'!':''}}</text><text y="-16">{{translateLocation(destination)}}</text></g>
          <g v-if="compact && compactRobotPoint" class="robot-node" :style="{ '--robot-color':selectedTheme.main }" :transform="`translate(${compactRobotPoint.x} ${compactRobotPoint.y})`"><rect x="-10" y="-10" width="20" height="20" rx="6"/><text y="27">{{robotId}}</text></g>
          <g v-for="location in locations" :key="location.id" class="location-node" :class="{'is-readonly':readOnly}" :transform="`translate(${mapPoint(location).x} ${mapPoint(location).y})`" @pointerdown.stop @click="!readOnly && (selected=location, emit('select-destination', location.label))">
            <circle :class="{ charger: location.isCharger, origin: origin===location.label, destination: destination===location.label }" r="7" />
            <text y="-12">{{ translateLocation(location.label) }}</text>
          </g>
          <g v-if="mainEntrance" class="location-node entrance-node" :transform="`translate(${mapPoint(mainEntrance).x} ${mapPoint(mainEntrance).y})`"><circle r="6"/><text y="-12">Main Entrance</text></g>
          <g v-if="!compact" v-for="robot in robotPoints" :key="robot.id" :style="{ '--robot-color': getRobotVisualTheme(robot.id).main }" :transform="`translate(${mapPoint(robot.location).x} ${mapPoint(robot.location).y})`" class="robot-node"><rect x="-8" y="-8" width="16" height="16" rx="5"/><text y="23">{{ robot.id }}</text></g>
        </g>
      </svg>
      <div v-else class="map-loading">{{t('map.loading')}}</div>
      <article v-if="selected" class="map-location-card">
        <button type="button" class="close-card" aria-label="關閉" @click="selected=null">×</button>
        <strong>{{ selected.label }}</strong>
        <span>目前等待任務：{{ selected.queued }}</span><span>最近機器人：{{ selected.robot }}</span><span>距離：{{ selected.name === 'reception_back' ? '12.4' : '18.6' }} m</span>
        <button type="button" class="destination-button" @click="emit('select-destination', selected.label)">設為目的地</button>
      </article>
      <div class="map-legend"><span><i class="origin-dot"></i>{{t('map.origin')}}</span><span><i class="destination-dot"></i>{{t('map.destination')}}</span><span><i class="robot-dot"></i>{{t('map.robot')}} {{historical?robotId:''}}</span></div>
    </div>
  </section>
</template>

<style scoped>
.mini-map{position:relative;box-sizing:border-box;height:100%;min-width:0;min-height:0;overflow:hidden;color:var(--text-primary);background:color-mix(in srgb,var(--scene-bg) 72%,var(--panel-bg));border:1px solid var(--panel-border);border-radius:6px;box-shadow:var(--glass-shadow)}.map-title{position:absolute;z-index:5;top:14px;left:16px;display:grid;gap:2px;pointer-events:none}.map-title strong{font-size:14px}.map-title span{color:var(--text-muted);font-size:10.5px}.map-controls{position:absolute;z-index:8;top:12px;right:13px;display:flex;gap:5px}.map-controls button{height:29px;min-width:29px;padding:0 8px;color:var(--text-secondary);font-size:11.5px;background:var(--panel-bg-strong);border:1px solid var(--panel-border);border-radius:5px;box-shadow:var(--control-shadow);cursor:pointer}.map-controls button:hover{color:var(--text-primary);background:var(--icon-button-hover)}.map-stage{position:absolute;inset:0;min-height:0;overflow:hidden;background:transparent}svg{display:block;width:100%;height:100%;border-radius:0;cursor:grab;touch-action:none;overscroll-behavior:contain}svg:active{cursor:grabbing}.building-footprint{fill:transparent;stroke:none}.map-lane{stroke:#b1a48f;stroke-width:3;stroke-linecap:round;opacity:.5}.estimate-route{fill:none;stroke:var(--route-color);stroke-width:6;stroke-linecap:round;stroke-linejoin:round}.location-node{cursor:pointer}.location-node circle{fill:#ad8c62;stroke:var(--panel-bg-strong);stroke-width:3}.location-node circle.charger{fill:#d38a56}.location-node circle.origin{fill:var(--route-color);fill-opacity:.45;stroke-width:4}.location-node circle.destination{fill:var(--route-color);stroke-width:4}.location-node text,.robot-node text{fill:var(--text-primary);font-size:10px;text-anchor:middle;paint-order:stroke;stroke:var(--panel-bg-strong);stroke-width:3px}.robot-node rect{fill:var(--robot-color);fill-opacity:.72;stroke:var(--robot-color);stroke-width:2}.map-loading{display:grid;height:100%;place-items:center;color:var(--text-muted)}
.map-location-card{position:absolute;z-index:9;right:14px;bottom:38px;display:grid;width:184px;gap:5px;padding:12px;color:var(--text-secondary);font-size:11.5px;background:var(--popover-bg);border:1px solid var(--panel-border);border-radius:12px;box-shadow:var(--dropdown-shadow);backdrop-filter:blur(20px)}.map-location-card strong{color:var(--text-primary);font-size:13px}.close-card{position:absolute;top:5px;right:6px;color:var(--text-muted);background:transparent;border:0;cursor:pointer}.destination-button{margin-top:4px;padding:7px;color:#fffaf2;background:var(--accent-orange);border:0;border-radius:7px;cursor:pointer}.map-legend{position:absolute;z-index:5;right:14px;bottom:12px;display:flex;gap:10px;color:var(--text-muted);font-size:10px}.map-legend span{display:flex;align-items:center;gap:4px}.map-legend i{width:7px;height:7px;border-radius:50%}.origin-dot{background:var(--route-color);opacity:.48}.destination-dot{background:var(--route-color)}.robot-dot{background:var(--route-color);border:1px solid color-mix(in srgb,var(--route-color) 75%,#333)}
.is-compact{border-radius:10px;background:linear-gradient(145deg,rgba(230,236,232,.85),rgba(245,248,246,.78))}.is-compact .map-stage{background:radial-gradient(circle at 45% 40%,rgba(255,255,255,.68),transparent 65%)}.is-compact .map-controls{top:9px;right:9px}.is-compact .map-controls button{height:26px;min-width:26px}.is-compact .map-lane{stroke:#8c9a94;stroke-width:2.5;opacity:.27}.is-compact .location-node:not(:has(.origin,.destination)){opacity:.42}.is-compact .location-node text{display:none}.is-compact .location-node circle{r:5}.is-compact .compact-route{stroke:#c96b35;stroke-width:8;filter:drop-shadow(0 2px 5px rgba(201,107,53,.24))}.compact-endpoint circle{fill:#fff8ef;stroke:#ce7137;stroke-width:5}.compact-endpoint.is-destination circle{fill:#ce7137;stroke:#fff8ef}.compact-endpoint text{fill:#384944;font-size:17px;font-weight:700;text-anchor:middle;paint-order:stroke;stroke:#f6faf7;stroke-width:5px}.is-compact .robot-node rect{fill:#238d7d;stroke:#fff;stroke-width:4}.is-compact .robot-node text{font-size:17px;font-weight:800}.is-compact .map-legend{font-size:10.5px;color:#51605a;background:rgba(255,255,255,.7);padding:5px 7px;border-radius:6px}.is-readonly{cursor:default}
.is-historical{background:color-mix(in srgb,var(--scene-bg) 72%,var(--panel-bg));border-radius:var(--radius-panel);box-shadow:var(--glass-shadow)}
.is-historical .map-stage{background:transparent}.is-historical .map-lane{stroke:#b1a48f;stroke-width:3;opacity:.5}
.is-historical .estimate-route{stroke:var(--route-color);stroke-width:6;filter:none;stroke-dasharray:none}
.is-historical .compact-endpoint circle{fill:var(--panel-bg-strong);stroke:var(--route-color);stroke-width:3}
.is-historical .compact-endpoint.is-destination circle{fill:var(--history-status-color);stroke:var(--panel-bg-strong);stroke-width:3}
.is-historical .compact-endpoint .endpoint-state{fill:#fff;stroke:none;paint-order:normal;font-size:13px;font-weight:700}
.is-historical .robot-node rect{fill:var(--robot-color);fill-opacity:.72;stroke:var(--robot-color);stroke-width:2}
.is-historical .map-legend{color:var(--text-secondary);background:var(--panel-background-strong)}
.mini-map:not(.is-historical) .estimate-route{stroke-dasharray:1;stroke-dashoffset:1;animation:map-route-draw 3s cubic-bezier(.22,.8,.3,1) forwards}.mini-map:not(.is-historical) .compact-endpoint{opacity:0;animation:map-marker-enter 1.5s ease-out .35s forwards}.mini-map:not(.is-historical) .robot-node{opacity:0;animation:map-marker-enter 1.5s ease-out .5s forwards}.mini-map:not(.is-historical) .location-node{opacity:0;animation:map-marker-enter 1.8s ease-out .2s forwards}@keyframes map-route-draw{to{stroke-dashoffset:0}}@keyframes map-marker-enter{to{opacity:1}}@media(prefers-reduced-motion:reduce){.mini-map:not(.is-historical) .estimate-route,.mini-map:not(.is-historical) .compact-endpoint,.mini-map:not(.is-historical) .robot-node,.mini-map:not(.is-historical) .location-node{animation:none;opacity:1}.mini-map:not(.is-historical) .estimate-route{stroke-dashoffset:0}}
</style>
