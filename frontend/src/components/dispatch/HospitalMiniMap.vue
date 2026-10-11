<script setup>
import { computed, onBeforeUnmount, onMounted, ref, useId, watch } from 'vue'
import { locationDetails, shortestVertexPath } from '@/data/demoActiveRoutes.js'
import { NAVIGATION_ASSETS } from '@/config/sceneAssets.js'
import { getRobotVisualTheme } from '@/config/robotVisualThemes.js'
import { historyStatusColors } from '@/data/historyPresentation.js'
import { t, translateLocation } from '@/i18n/index.js'
import { fitMapToViewport, getMapBounds, getRoomSelectableWaypoints, rmfToMapPoint } from './dispatchMapGeometry.js'

const props = defineProps({
  robots: { type: Array, required: true }, destination: { type: String, default: '' }, origin: { type: String, default: '' },
  robotId: { type: String, default: 'R01' }, compact: { type: Boolean, default: false }, readOnly: { type: Boolean, default: false },
  routeCoordinates: { type: Array, default: () => [] }, routeProgress: { type: Number, default: 0.5 },
  historical: { type: Boolean, default: false }, historyStatus: { type: String, default: '' },
  selectionMode: { type: String, default: 'destination' }, allowedLocations: { type: Array, default: () => Object.values(locationDetails).map(({label}) => label) },
  viewportInsets: { type: Object, default: () => ({ left: 20, right: 20, top: 88, bottom: 72 }) },
})
const emit = defineEmits(['select-origin', 'select-destination'])
const root = ref(null), svg = ref(null), data = ref(null), floorplan = ref(null)
const selected = ref(null), roomChoices = ref([]), loading = ref(true), error = ref(''), floorError = ref('')
const viewport = ref({ width: 850, height: 600 })
const zoom = ref(1), pan = ref({ x: 0, y: 0 }), drag = ref(null)
const id = useId().replace(/:/g, '')
const shadowId = `room-shadow-${id}`, arrowId = `route-arrow-${id}`
const controller = new AbortController()
let observer
const mapPoint = rmfToMapPoint
onMounted(async () => {
  observer = new ResizeObserver(([entry]) => {
    if (entry.contentRect.width > 0 && entry.contentRect.height > 0) viewport.value = { width: entry.contentRect.width, height: entry.contentRect.height }
  })
  observer.observe(root.value)
  const getJson = async (url) => {
    const response = await fetch(url, { signal: controller.signal, cache: 'no-store' })
    if (!response.ok) throw new Error('無法讀取地圖資料')
    return response.json()
  }
  await Promise.all([
    getJson(NAVIGATION_ASSETS.graph0).then((value) => { data.value = value }).catch((reason) => { if (reason.name !== 'AbortError') error.value = '導航資料載入失敗，請重新整理。' }),
    props.compact ? Promise.resolve() : getJson(`${import.meta.env.BASE_URL}generated/hospital-floorplan.json`).then((value) => { floorplan.value = value }).catch((reason) => { if (reason.name !== 'AbortError') floorError.value = '房間圖層暫時無法載入；仍可使用站點與路線。' }),
  ])
  loading.value = false
})
onBeforeUnmount(() => { controller.abort(); observer?.disconnect() })
const vertices = computed(() => new Map((data.value?.vertices || []).map((vertex) => [vertex.id, vertex])))
const locations = computed(() => (data.value?.namedWaypoints || []).filter((point) => locationDetails[point.name]).map((point) => ({ ...point, ...locationDetails[point.name] })))
const namedByLabel = computed(() => new Map(locations.value.map((point) => [point.label, point])))
const allowedNames = computed(() => locations.value.filter(({label}) => props.allowedLocations.includes(label)).map(({name}) => name))
const canSelect = (location) => !props.readOnly && props.allowedLocations.includes(location.label)
const laneLines = computed(() => {
  const seen = new Set()
  return (data.value?.lanes || []).flatMap((lane) => {
    const key = [lane.from, lane.to].sort().join('|')
    if (seen.has(key) || !vertices.value.has(lane.from) || !vertices.value.has(lane.to)) return []
    seen.add(key)
    return [{ id: lane.id, a: mapPoint(vertices.value.get(lane.from)), b: mapPoint(vertices.value.get(lane.to)) }]
  })
})
const mainEntrance = computed(() => {
  const points = data.value?.doors?.find(({name}) => name === 'main_entrance')?.endpoints
  return points?.length ? { label: 'Main Entrance', x: points.reduce((sum, p) => sum + p[0], 0) / points.length, y: points.reduce((sum, p) => sum + p[1], 0) / points.length } : null
})
const robotPoints = computed(() => props.robots.flatMap((robot) => {
  // Explicit RMF poses only; never infer the frame of an arbitrary position.
  const pose = robot.rmfPosition
  const location = pose?.level === 'L1' && Number.isFinite(pose.x) && Number.isFinite(pose.y)
    ? pose : namedByLabel.value.get(robot.currentLocation) || data.value?.namedWaypoints?.find(({name}) => name === robot.currentWaypoint) || (robot.currentLocation === 'Main Entrance' ? mainEntrance.value : null)
  return location ? [{ ...robot, location }] : []
}))
const routePoints = computed(() => {
  if (props.compact && props.routeCoordinates.length) return props.routeCoordinates.map(([x,y]) => ({x,y}))
  const start = namedByLabel.value.get(props.origin), end = namedByLabel.value.get(props.destination)
  if (!start || !end || !data.value) return []
  return shortestVertexPath(data.value, start.id, end.id).map((vertexId) => mapPoint(vertices.value.get(vertexId)))
})
const routeUnavailable = computed(() => !loading.value && data.value && props.origin && props.destination && !routePoints.value.length)
const roomPalette = { consultation: ['#f5d8c8','#d6b4a1'], ward: ['#d8e4da','#b3c7b6'], examination: ['#dae5ed','#b8cbd8'], charging: ['#eadfc0','#cabc94'], support: ['#e3ddec','#c6bbd4'], nursing: ['#d0e5df','#adc9c0'] }
const rooms = computed(() => (floorplan.value?.rooms || []).filter((room) => room.renderable && !room.isDemo).map((room) => {
  const points = room.polygon.map(mapPoint), bounds = getMapBounds(points)
  return { ...room, points: points.map(({x,y}) => `${x},${y}`).join(' '), labelX: (bounds.minX+bounds.maxX)/2, labelY: bounds.minY + 19, colors: roomPalette[room.category] || roomPalette.support,
    selectable: getRoomSelectableWaypoints(room, data.value, allowedNames.value) }
}))
const footprint = computed(() => (floorplan.value?.footprint || []).map(mapPoint).map(({x,y}) => `${x},${y}`).join(' '))
const walls = computed(() => (floorplan.value?.walls || []).map((wall) => ({ id: wall.sourceWallIndex, a: mapPoint(wall.endpoints[0]), b: mapPoint(wall.endpoints[1]) })))
const bounds = computed(() => getMapBounds([...(data.value?.vertices || []), ...(floorplan.value?.footprint || [])].map(mapPoint)))
const fit = computed(() => fitMapToViewport(bounds.value, viewport.value, props.viewportInsets, 12))
const resetView = () => { zoom.value = props.compact ? 1 : fit.value?.scale || 1; pan.value = props.compact ? {x:0,y:0} : {x:fit.value?.x || 0,y:fit.value?.y || 0} }
watch([fit, () => props.compact], resetView, { immediate: true })
const compactRobotPoint = computed(() => {
  const points = routePoints.value
  if (!points.length) return null
  if (props.historical) return {x:points.at(-1).x+20,y:points.at(-1).y+18}
  return points[Math.min(points.length-1,Math.max(0,Math.round((points.length-1)*props.routeProgress)))]
})
const compactViewBox = computed(() => {
  const b = getMapBounds(routePoints.value)
  if (!b) return '105 125 640 360'
  let width = Math.max(250,b.maxX-b.minX+150), height = Math.max(130,b.maxY-b.minY+110)
  if (width/height<2.45) width=height*2.45; else height=width/2.45
  return `${(b.minX+b.maxX-width)/2} ${(b.minY+b.maxY-height)/2} ${width} ${height}`
})
const transform = computed(() => `translate(${pan.value.x} ${pan.value.y}) scale(${zoom.value})`)
const selectedTheme = computed(() => getRobotVisualTheme(props.robotId))
const mapThemeStyle = computed(() => ({ '--route-color': selectedTheme.value.main, '--route-soft': selectedTheme.value.soft, '--history-status-color': historyStatusColors[props.historyStatus] || 'var(--theme-primary)', '--map-safe-left': `${props.viewportInsets.left || 20}px`, '--map-safe-right': `${props.viewportInsets.right || 20}px`, '--map-safe-bottom': `${props.viewportInsets.bottom || 72}px` }))
const svgPoint = (event) => {
  const matrix = svg.value?.getScreenCTM?.()
  if (!matrix) return {x:event.clientX,y:event.clientY}
  const point = svg.value.createSVGPoint(); point.x=event.clientX; point.y=event.clientY
  return point.matrixTransform(matrix.inverse())
}
const changeZoom = (factor, anchor) => {
  if (!anchor) {
    const rect = svg.value?.getBoundingClientRect()
    anchor = rect ? svgPoint({ clientX:rect.left + (props.compact ? rect.width/2 : ((props.viewportInsets.left || 0)+rect.width-(props.viewportInsets.right || 0))/2), clientY:rect.top+rect.height/2 }) : {x:425,y:300}
  }
  const base = props.compact ? 1 : fit.value?.scale || 1
  const next = Math.max(base*.65,Math.min(base*4,zoom.value*factor)), ratio=next/zoom.value
  pan.value = {x:anchor.x-(anchor.x-pan.value.x)*ratio,y:anchor.y-(anchor.y-pan.value.y)*ratio}; zoom.value=next
}
const onWheel = (event) => { event.preventDefault(); event.stopPropagation(); changeZoom(event.deltaY>0?.9:1.1,svgPoint(event)) }
const chooseLocation = (location) => {
  if (!location || !canSelect(location)) return
  selected.value=location; roomChoices.value=[]
  emit(props.selectionMode === 'origin' ? 'select-origin' : 'select-destination',location.label)
}
const chooseRoom = (room) => {
  if (props.readOnly || !room?.selectable.length) return
  const options = room.selectable.map((point) => namedByLabel.value.get(locationDetails[point.name]?.label)).filter(Boolean)
  if (options.length === 1) chooseLocation(options[0])
  else { selected.value=null; roomChoices.value=options }
}
const onPointerDown = (event) => {
  if (event.button !== 0 || drag.value) return
  const point = svgPoint(event)
  drag.value = { pointerId:event.pointerId, point, clientX:event.clientX, clientY:event.clientY, pan:{...pan.value}, moved:false, waypoint:event.target.closest?.('[data-waypoint]')?.dataset.waypoint, room:event.target.closest?.('[data-room]')?.dataset.room }
  svg.value?.setPointerCapture?.(event.pointerId)
}
const onPointerMove = (event) => {
  if (!drag.value || drag.value.pointerId !== event.pointerId) return
  if (Math.hypot(event.clientX-drag.value.clientX,event.clientY-drag.value.clientY)>5) drag.value.moved=true
  if (!drag.value.moved) return
  const point = svgPoint(event)
  pan.value = {x:drag.value.pan.x+point.x-drag.value.point.x,y:drag.value.pan.y+point.y-drag.value.point.y}
}
const onPointerUp = (event) => {
  if (!drag.value || drag.value.pointerId !== event.pointerId) return
  const gesture = drag.value
  const moved = gesture.moved || Math.hypot(event.clientX-gesture.clientX,event.clientY-gesture.clientY)>5
  drag.value=null
  if (svg.value?.hasPointerCapture?.(event.pointerId)) svg.value.releasePointerCapture(event.pointerId)
  if (event.type !== 'pointerup' || moved) return
  if (gesture.waypoint) chooseLocation(locations.value.find(({name}) => name===gesture.waypoint))
  else if (gesture.room) chooseRoom(rooms.value.find(({id}) => id===gesture.room))
}
</script>

<template>
  <section ref="root" class="mini-map" :class="{'is-compact':compact,'is-historical':historical,'is-workspace':!compact}" :style="mapThemeStyle" :aria-label="t('map.title')">
    <div v-if="!compact" class="map-title"><span class="map-eyebrow">HOSPITAL FLOOR PLAN <i>1F</i></span><strong>醫院平面地圖</strong><span>選取{{ selectionMode==='origin'?'起點':'目的地' }} · 點擊站點或對應房間</span></div>
    <div class="map-controls"><button type="button" :aria-label="t('map.zoomIn')" @click="changeZoom(1.15)">＋</button><button type="button" :aria-label="t('map.zoomOut')" @click="changeZoom(.87)">－</button><button v-if="!compact" type="button" @click="resetView">{{t('map.reset')}}</button></div>
    <div class="map-stage">
      <svg v-if="data" ref="svg" :viewBox="compact?compactViewBox:`0 0 ${viewport.width} ${viewport.height}`" @wheel="onWheel" @pointerdown="onPointerDown" @pointermove="onPointerMove" @pointerup="onPointerUp" @pointercancel="onPointerUp" @lostpointercapture="drag=null">
        <defs>
          <filter :id="shadowId" x="-25%" y="-25%" width="160%" height="170%"><feDropShadow dx="0" dy="5" stdDeviation="4" flood-color="#5e6b63" flood-opacity=".14"/></filter>
          <marker :id="arrowId" markerWidth="8" markerHeight="8" refX="5" refY="4" orient="auto" markerUnits="strokeWidth"><path d="M1 1 L6 4 L1 7" fill="none" stroke="#a75527" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></marker>
        </defs>
        <g class="map-world" :transform="transform">
          <polygon v-if="!compact && footprint" :points="footprint" class="floor-slab" :filter="`url(#${shadowId})`" />
          <g v-if="!compact" class="room-layer">
            <g v-for="room in rooms" :key="room.id" :data-room="room.id" class="room-region" :class="{'can-select':room.selectable.length&&!readOnly}" :style="{'--room-fill':room.colors[0],'--room-side':room.colors[1]}" :role="room.selectable.length&&!readOnly?'button':undefined" :tabindex="room.selectable.length&&!readOnly?0:undefined" :aria-label="room.label" @keydown.enter.prevent="chooseRoom(room)" @keydown.space.prevent="chooseRoom(room)" @click="$event.detail===0 && chooseRoom(room)">
              <title>{{room.label}}</title><polygon class="room-side" :points="room.points" transform="translate(0 4)" :filter="`url(#${shadowId})`"/><polygon class="room-top" :points="room.points"/><text class="room-label" :x="room.labelX" :y="room.labelY">{{room.label}}</text>
            </g>
            <line v-for="wall in walls" :key="wall.id" :x1="wall.a.x" :y1="wall.a.y" :x2="wall.b.x" :y2="wall.b.y" class="floor-wall" />
          </g>
          <line v-for="lane in laneLines" :key="lane.id" :x1="lane.a.x" :y1="lane.a.y" :x2="lane.b.x" :y2="lane.b.y" class="map-lane" />
          <polyline v-if="routePoints.length" pathLength="1" :points="routePoints.map((point) => `${point.x},${point.y}`).join(' ')" class="estimate-route" :class="{'compact-route':compact&&!historical}" :marker-mid="compact&&!historical?`url(#${arrowId})`:undefined" />
          <g v-if="compact && routePoints.length" class="compact-endpoint" :transform="`translate(${routePoints[0].x} ${routePoints[0].y})`"><circle r="9"/><text y="-16">{{translateLocation(origin)}}</text></g>
          <g v-if="compact && routePoints.length" class="compact-endpoint is-destination" :transform="`translate(${routePoints.at(-1).x} ${routePoints.at(-1).y})`"><circle r="9"/><text v-if="historical" class="endpoint-state" y="5">{{historyStatus==='completed'?'✓':historyStatus==='cancelled'?'×':historyStatus==='failed'?'!':''}}</text><text y="-16">{{translateLocation(destination)}}</text></g>
          <g v-if="compact && compactRobotPoint" class="robot-node" :style="{ '--robot-color':selectedTheme.main }" :transform="`translate(${compactRobotPoint.x} ${compactRobotPoint.y})`"><rect x="-10" y="-10" width="20" height="20" rx="6"/><text y="27">{{robotId}}</text></g>
          <g v-for="location in locations" :key="location.id" :data-waypoint="location.name" class="location-node" :class="{'is-readonly':!canSelect(location)}" :transform="`translate(${mapPoint(location).x} ${mapPoint(location).y})`" :role="canSelect(location)?'button':undefined" :tabindex="canSelect(location)?0:undefined" :aria-label="`${translateLocation(location.label)}${canSelect(location)?'':'（不可派遣）'}`" @keydown.enter.prevent="chooseLocation(location)" @keydown.space.prevent="chooseLocation(location)" @click="$event.detail===0 && chooseLocation(location)">
            <circle class="station-hit" r="15"/><circle v-if="origin===location.label || destination===location.label" class="station-halo" r="13"/>
            <circle :class="{ charger: location.isCharger, origin: origin===location.label, destination: destination===location.label }" r="6" />
            <text v-if="compact || !rooms.some(room=>room.waypointNames.includes(location.name))" y="-17">{{ translateLocation(location.label) }}</text>
          </g>
          <g v-if="mainEntrance" class="entrance-node" :transform="`translate(${mapPoint(mainEntrance).x} ${mapPoint(mainEntrance).y})`"><circle r="3"/><text y="20">主入口</text></g>
          <g v-if="!compact" class="robot-layer"><g v-for="robot in robotPoints" :key="robot.id" :data-robot="robot.id" :style="{ '--robot-color': getRobotVisualTheme(robot.id).main }" :transform="`translate(${mapPoint(robot.location).x} ${mapPoint(robot.location).y})`" class="robot-node"><rect x="-8" y="-8" width="16" height="16" rx="5"/><path d="M-3 2 L0 -3 L3 2" fill="none" stroke="white" stroke-width="1.8"/><text y="25">{{ robot.id }}</text></g></g>
        </g>
      </svg>
      <div v-else class="map-loading" role="status">{{error || t('map.loading')}}</div>
      <article v-if="!compact && (selected || roomChoices.length)" class="map-location-card">
        <button type="button" class="close-card" aria-label="關閉站點資訊" @click="selected=null;roomChoices=[]">×</button>
        <template v-if="selected"><strong>{{ translateLocation(selected.label) }}</strong><span>已設為{{selectionMode==='origin'?'起點':'目的地'}}</span></template>
        <template v-else><strong>選擇房間內的站點</strong><button v-for="choice in roomChoices" :key="choice.name" class="destination-button" @click="chooseLocation(choice)">{{translateLocation(choice.label)}}</button></template>
      </article>
      <div v-if="!compact" class="map-caption"><span class="demo-indicator">示範機器人資料</span><span v-if="floorError">{{floorError}}</span><span v-else>部分區域尚無完整邊界，僅顯示站點</span><strong v-if="routeUnavailable" role="status">目前起終點之間沒有可用路線</strong></div>
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

.is-workspace{border:0;border-radius:0;box-shadow:none;background:radial-gradient(ellipse at 60% 40%,#fafbf9 0%,#eef1ed 85%)}.is-workspace .map-title{top:26px;left:var(--map-safe-left);gap:6px}.is-workspace .map-title strong{font-size:21px;letter-spacing:.8px;font-weight:600}.map-eyebrow{font-size:9px!important;letter-spacing:1.8px;display:flex;align-items:center;gap:12px}.map-eyebrow i{font-style:normal;letter-spacing:0;padding:3px 7px;background:#fff9;border:1px solid #d9dfd8;border-radius:4px}.is-workspace .map-controls{top:28px;right:24px}.is-workspace .map-controls button{height:34px;min-width:34px;border-radius:5px}.floor-slab{fill:#f8f9f6;stroke:#d6dcd4;stroke-width:2;stroke-linejoin:round}.room-top{fill:var(--room-fill);stroke:#ffffffc9;stroke-width:1.8;stroke-linejoin:round}.room-side{fill:var(--room-side);stroke:var(--room-side);stroke-width:1;stroke-linejoin:round}.room-label{fill:#4a5654;font-size:10px;font-weight:550;text-anchor:middle;pointer-events:none}.room-region.can-select{cursor:pointer}.room-region.can-select:hover .room-top,.room-region:focus .room-top{stroke:#ed9c6c;stroke-width:2.5}.floor-wall{stroke:#99a69b;stroke-width:1.6;stroke-linecap:round;opacity:.32;pointer-events:none}.is-workspace .map-lane{stroke:#a6b4aa;stroke-width:1.6;opacity:.6;pointer-events:none}.is-workspace .estimate-route{stroke:#ee9767;stroke-width:4;filter:drop-shadow(0 2px 3px #ee976733);pointer-events:none;animation:none;stroke-dashoffset:0}.is-workspace .location-node,.is-workspace .robot-node{animation:none;opacity:1}.location-node .station-hit{fill:transparent;stroke:none}.location-node .station-halo{fill:none;stroke:#ee9767;stroke-width:2;opacity:.6}.location-node:focus{outline:none}.location-node:focus .station-hit{stroke:#835d3d;stroke-width:2}.is-workspace .location-node circle:not(.station-hit):not(.station-halo){fill:#a4b4a7;stroke:#fff;stroke-width:2}.is-workspace .location-node circle.origin{fill:#fff!important;stroke:#ee9767!important;fill-opacity:1}.is-workspace .location-node circle.destination{fill:#ee9767!important}.is-workspace .location-node text{font-size:11px;stroke:#f9faf7;stroke-width:4px;pointer-events:none}.robot-layer{pointer-events:none}.is-workspace .robot-node rect{fill:var(--robot-color);stroke:#fff;stroke-width:2;fill-opacity:1;filter:drop-shadow(0 2px 3px #45504722)}.robot-node text{font-size:10px}.entrance-node{fill:#92a198;pointer-events:none}.entrance-node text{fill:#819087;font-size:10px;text-anchor:middle}.map-caption{position:absolute;left:var(--map-safe-left);bottom:calc(var(--map-safe-bottom) - 18px);display:flex;gap:12px;flex-wrap:wrap;max-width:calc(100% - var(--map-safe-left) - 160px);color:var(--text-muted);font-size:10px;pointer-events:none}.demo-indicator{color:var(--text-secondary)}.demo-indicator:before{content:'';display:inline-block;width:5px;height:5px;background:#b6bdad;border-radius:50%;margin-right:5px}.map-caption strong{color:#a85637;font-weight:500}.is-workspace .map-legend{bottom:calc(var(--map-safe-bottom) - 18px);right:24px}.is-workspace .map-location-card{bottom:calc(var(--map-safe-bottom) + 16px);border-radius:6px;width:auto;min-width:160px}.is-workspace .origin-dot{background:#fff;border:1px solid #ee9767;opacity:1}.is-workspace .destination-dot{background:#ee9767}.is-workspace .map-loading{padding-left:var(--map-safe-left);box-sizing:border-box}.is-readonly{opacity:.5!important;cursor:default}
:global([data-theme='dark']) .is-workspace{background:radial-gradient(ellipse at 60% 40%,#424d46,#303b35)}:global([data-theme='dark']) .floor-slab{fill:#566158;stroke:#6f7f72}:global([data-theme='dark']) .room-top{fill:color-mix(in srgb,var(--room-fill) 55%,#526259);stroke:#d1dacf66}:global([data-theme='dark']) .room-side{fill:color-mix(in srgb,var(--room-side) 55%,#3d4941);stroke:#738076}:global([data-theme='dark']) .room-label{fill:#26382e}:global([data-theme='dark']) .is-workspace .location-node text{stroke:#566158}
@media(max-width:899px){.is-workspace{border:1px solid var(--panel-border);border-radius:8px}.is-workspace .map-title{top:16px;left:16px}.is-workspace .map-title strong{font-size:17px}.is-workspace .map-controls{top:18px;right:12px}.is-workspace .map-controls button{height:29px;min-width:27px;font-size:10px}.map-eyebrow{font-size:8px!important;letter-spacing:.8px}.map-caption{left:16px;bottom:37px;max-width:calc(100% - 32px);font-size:9px;gap:6px}.is-workspace .map-legend{bottom:14px;right:16px}.is-workspace .map-location-card{bottom:75px}}
</style>
