<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import * as THREE from 'three'
import { createGltfLoader, runtimeModelUrl } from '@/three/loaders/createGltfLoader.js'
import { COMPRESSED_MODELS } from '@/config/compressedModels.js'
import { MapControls } from 'three/addons/controls/MapControls.js'
import { Line2 } from 'three/addons/lines/Line2.js'
import { LineGeometry } from 'three/addons/lines/LineGeometry.js'
import { LineMaterial } from 'three/addons/lines/LineMaterial.js'
import { LineSegments2 } from 'three/addons/lines/LineSegments2.js'
import { LineSegmentsGeometry } from 'three/addons/lines/LineSegmentsGeometry.js'
import { SCENE_ASSETS, NAVIGATION_ASSETS } from '@/config/sceneAssets.js'
import { dispatchFloors, dispatchLocations, isDispatchPreview, modelObjectName } from '@/config/dispatchMap.js'
import { dispatchWaypointLabels } from '@/config/dispatchDestinations.js'
import { routeDisplayPoints, shortestLanePath, validateDispatchMapping, waypointDisplayPoint } from './dispatchRouteMapping.js'
import { RotateCcw } from '@lucide/vue'
import { getRobotVisualTheme } from '@/config/robotVisualThemes.js'
import { rmfToThree } from '@/config/rmfMapTransform.js'
import { normalizeFloor } from '@/data/overviewStatusData.js'
import { robotDisplayCode } from '@/config/robotDisplayCode.js'
import { defaultDispatchModelPreset, readDispatchCameraPreset, readDispatchModelPreset, storeDispatchCameraPreset, storeDispatchModelPreset, validDispatchCameraPreset, validDispatchModelPreset } from '@/config/dispatchViewPreset.js'
import { t, translateLocation } from '@/i18n/index.js'
import SharedLoading from '@/components/SharedLoading.vue'
import { readModelResponse } from './readModelResponse.js'

const props = defineProps({
  robots: { type: Array, required: true }, robotId: String, source: String, destination: String,
  selectionStep: { type: Number, default: 0 }, routeConfirmed: { type: Boolean, default: false },
  showSourcePin: { type: Boolean, default: false }, showDestinationPin: { type: Boolean, default: false },
  allowedLocations: { type: Array, default: () => [] },
  viewportInsets: { type: Object, default: () => ({ left: 0, right: 0, top: 0, bottom: 0 }) },
})
const emit = defineEmits(['select-location', 'visual-top-change'])
const host = ref(null), loading = ref(true), error = ref(''), graph = ref(null), mapping = ref(null), markers = ref([])
const modelProgress = ref(0)
const activeFloor = ref(1), floorPickerOpen = ref(false), floorPicker = ref(null), graphError = ref('')
function onFloorPickerOutside(event) {
  if (!floorPicker.value?.contains(event.target)) floorPickerOpen.value = false
}
function selectFloor(floor) {
  activeFloor.value = floor.id
  floorPickerOpen.value = false
}
onMounted(() => document.addEventListener('pointerdown', onFloorPickerOutside))
const robotMarkers = ref([])
const params = new URLSearchParams(window.location.search)
const cameraDebugEnabled = params.get('cameraDebug') === '1'
const modelDebugEnabled = params.get('modelDebug') === '1'
const debugEnabled = cameraDebugEnabled || modelDebugEnabled
const FACTORY_DISPATCH_ZOOM = 1.12
const debugStatus = ref('')
const cameraPreset = reactive({ position: { x: 0, y: 48, z: 27 }, target: { x: 0, y: 0, z: 0 }, zoom: 1 })
const modelPreset = reactive(readDispatchModelPreset() || defaultDispatchModelPreset())
let scene, camera, renderer, controls, observer, frame, model, disposed = false, down, modelScenes = []
let overlay, routeLayer, mapRoot, roomVisualBounds, defaultTarget, defaultPosition, factoryTarget, factoryPosition, defaultZoom = 1, viewSpan = 32
let lastVisualTop = null
const selectable = [], resources = new Set(), abort = new AbortController()
const raycaster = new THREE.Raycaster()
const size = { width: 1, height: 1 }
const mapStyle = computed(() => ({ '--safe-left': `${props.viewportInsets.left + 12}px`, '--safe-right': `${props.viewportInsets.right + 12}px` }))
const allowed = (name) => props.allowedLocations.includes(name)
function captureCamera() {
  if (!debugEnabled || !camera || !controls) return
  const display = (value) => Math.round(value * 1000) / 1000
  Object.assign(cameraPreset.position, { x: display(camera.position.x), y: display(camera.position.y), z: display(camera.position.z) })
  Object.assign(cameraPreset.target, { x: display(controls.target.x), y: display(controls.target.y), z: display(controls.target.z) })
  cameraPreset.zoom = display(camera.zoom)
}
function applyCameraPreset() {
  if (!camera || !controls || !validDispatchCameraPreset(cameraPreset)) return
  camera.position.set(Number(cameraPreset.position.x), Number(cameraPreset.position.y), Number(cameraPreset.position.z))
  controls.target.set(Number(cameraPreset.target.x), Number(cameraPreset.target.y), Number(cameraPreset.target.z))
  camera.zoom = Number(cameraPreset.zoom)
  camera.updateProjectionMatrix(); controls.update()
}
function applyModelPreset() {
  if (!mapRoot || !validDispatchModelPreset(modelPreset)) return
  mapRoot.position.set(Number(modelPreset.position.x), Number(modelPreset.position.y), Number(modelPreset.position.z))
  mapRoot.rotation.y = Number(modelPreset.rotationY)
  mapRoot.scale.setScalar(Number(modelPreset.scale))
  mapRoot.updateMatrixWorld(true)
  syncPanelTop()
}
function syncPanelTop() {
  if (disposed || loading.value || !roomVisualBounds || !camera || !mapRoot) return
  mapRoot.updateMatrixWorld(true)
  camera.updateMatrixWorld()
  let firstRoomPixel = Infinity
  for (const x of [roomVisualBounds.min.x, roomVisualBounds.max.x]) {
    for (const y of [roomVisualBounds.min.y, roomVisualBounds.max.y]) {
      for (const z of [roomVisualBounds.min.z, roomVisualBounds.max.z]) {
        const projected = mapRoot.localToWorld(new THREE.Vector3(x, y, z)).project(camera)
        firstRoomPixel = Math.min(firstRoomPixel, (1 - projected.y) * size.height / 2)
      }
    }
  }
  const offset = Math.round(Math.min(Math.max(10, firstRoomPixel + 8), Math.max(10, size.height - 550)))
  if (Number.isFinite(offset) && offset !== lastVisualTop) {
    lastVisualTop = offset
    emit('visual-top-change', offset)
  }
}
function saveDebugPreset() {
  captureCamera()
  if (!validDispatchCameraPreset(cameraPreset) || !validDispatchModelPreset(modelPreset)) { debugStatus.value = t('dispatchDebug.invalid'); return }
  try {
    storeDispatchCameraPreset(cameraPreset); storeDispatchModelPreset(modelPreset)
    defaultPosition.copy(camera.position); defaultTarget.copy(controls.target); defaultZoom = camera.zoom
    controls.saveState(); debugStatus.value = t('dispatchDebug.saved')
  } catch { debugStatus.value = t('dispatchDebug.saveFailed') }
}
function resetDebugPreset() {
  Object.assign(modelPreset, defaultDispatchModelPreset())
  applyModelPreset()
  camera.position.copy(factoryPosition); controls.target.copy(factoryTarget); camera.zoom = FACTORY_DISPATCH_ZOOM
  camera.updateProjectionMatrix(); controls.update(); captureCamera()
  debugStatus.value = t('dispatchDebug.reset')
}
async function copyDebugPreset() {
  captureCamera()
  try { await navigator.clipboard.writeText(JSON.stringify({ camera: cameraPreset, model: modelPreset }, null, 2)); debugStatus.value = t('dispatchDebug.copied') }
  catch { debugStatus.value = t('dispatchDebug.copyFailed') }
}

function disposeObject(root) {
  root?.traverse((object) => {
    if (object.geometry) resources.add(object.geometry)
    for (const material of [object.material].flat().filter(Boolean)) {
      resources.add(material)
      Object.values(material).forEach((value) => { if (value?.isTexture) resources.add(value) })
    }
  })
}
function clearOverlay() {
  if (!overlay) return
  overlay.traverse((object) => { object.geometry?.dispose(); for (const material of [object.material].flat().filter(Boolean)) material.dispose() })
  overlay.clear()
}
function addLines(group, segments, color, width, opacity = 1) {
  if (!segments.length) return
  const geometry = new LineSegmentsGeometry()
  geometry.setPositions(segments.flatMap(([a, b]) => [...a, ...b]))
  const material = new LineMaterial({ color, linewidth: width, transparent: opacity < 1, opacity, depthTest: true })
  material.resolution.set(size.width, size.height)
  group.add(new LineSegments2(geometry, material))
}
function addPath(group, points, color, width) {
  if (points.length < 2) return
  const geometry = new LineGeometry()
  geometry.setPositions(points.flat())
  const material = new LineMaterial({ color, linewidth: width, depthTest: true })
  material.resolution.set(size.width, size.height)
  group.add(new Line2(geometry, material))
}
function clearGroup(group) {
  group?.traverse((object) => { object.geometry?.dispose(); for (const material of [object.material].flat().filter(Boolean)) material.dispose() })
  group?.clear()
}
function displayEdgeKey(a, b) { return [a, b].sort().join('::') }
function drawRouteNetwork(mapData) {
  clearGroup(routeLayer)
  const navigable = new Set()
  for (const lane of Object.values(mapData.lanes)) {
    for (let index = 1; index < lane.displayNodes.length; index++) {
      navigable.add(displayEdgeKey(lane.displayNodes[index - 1], lane.displayNodes[index]))
    }
  }
  const main = [], visualOnly = []
  for (const edge of Object.values(mapData.displayEdges)) {
    const [a, b] = edge.nodes
    const start = mapData.displayNodes[a]?.position, end = mapData.displayNodes[b]?.position
    if (!start || !end) continue
    const segment = [[start[0], start[1] + .025, start[2]], [end[0], end[1] + .025, end[2]]]
    ;(navigable.has(displayEdgeKey(a, b)) ? main : visualOnly).push(segment)
  }
  addLines(routeLayer, main, '#DAC9A6', 3.5)
  addLines(routeLayer, visualOnly, '#DAC9A6', 2.5, .7)
}
function updateOverlay() {
  if (!overlay || !graph.value || !mapping.value) return
  clearOverlay()
  const start = graph.value.namedWaypoints.find((p) => p.name === props.source)
  const end = graph.value.namedWaypoints.find((p) => p.name === props.destination)
  if (props.routeConfirmed && start && end) {
    const laneIds = shortestLanePath(graph.value, start.id, end.id, mapping.value)
    const points = routeDisplayPoints(mapping.value, laneIds)
    addPath(overlay, points.map(([x, y, z]) => [x, y + .055, z]), '#F75C2F', 5.5)
  }
}
function choose(name) {
  if (!allowed(name) || !graph.value?.namedWaypoints.some((point) => point.name === name)) return
  emit('select-location', name)
}
async function sha256Hex(buffer) {
  const digest = await crypto.subtle.digest('SHA-256', buffer)
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, '0')).join('')
}
function projectMarkers() {
  if (!camera || !model) return
  const next = []
  for (const station of (mapping.value && graph.value?.namedWaypoints) || []) {
    const name = station.name
    const isSource = props.showSourcePin && props.source === name
    const isDestination = props.showDestinationPin && props.destination === name
    if (!allowed(name) && !isSource && !isDestination) continue
    const position = waypointDisplayPoint(mapping.value, station.id)
    if (!position) continue
    const point = mapRoot.localToWorld(new THREE.Vector3(...position)).project(camera)
    const label = dispatchWaypointLabels[name]
    next.push({ name, label, x: (point.x + 1) * size.width / 2, y: (1 - point.y) * size.height / 2, visible: point.z >= -1 && point.z <= 1, source: isSource, destination: isDestination })
  }
  robotMarkers.value = props.robots.flatMap((robot) => {
    if (!robot.hasTelemetry || robot.state === 'offline' || normalizeFloor(robot.levelName) !== 'floor1'
      || ![robot.x, robot.y].every(Number.isFinite)) return []
    const position = rmfToThree(robot)
    const point = mapRoot.localToWorld(new THREE.Vector3(position.x, position.y + .4, position.z)).project(camera)
    return [{ id: robot.id, displayCode: robotDisplayCode(robot.id),
      x: (point.x + 1) * size.width / 2, y: (1 - point.y) * size.height / 2,
      color: getRobotVisualTheme(robot.id).main, visible: point.z >= -1 && point.z <= 1 }]
  })
  markers.value = next
}
function resize() {
  if (!renderer || !host.value) return
  size.width = Math.max(host.value.clientWidth, 1); size.height = Math.max(host.value.clientHeight, 1)
  renderer.setSize(size.width, size.height)
  for (const group of [routeLayer, overlay]) group?.traverse((object) => { if (object.material?.resolution) object.material.resolution.set(size.width, size.height) })
  const span = viewSpan, aspect = size.width / size.height
  camera.left = -span * aspect / 2; camera.right = span * aspect / 2
  camera.top = span / 2; camera.bottom = -span / 2
  const { left = 0, right = 0, top = 0, bottom = 0 } = props.viewportInsets
  camera.setViewOffset(size.width, size.height, (right - left) / 2, (bottom - top) / 2, size.width, size.height)
  camera.updateProjectionMatrix()
  syncPanelTop()
  // Keep the user's target and zoom on resize; only update projection.
}
function resetView() {
  if (!defaultTarget || !controls) return
  controls.reset()
  camera.position.copy(defaultPosition); controls.target.copy(defaultTarget); camera.zoom = defaultZoom
  const { left = 0, right = 0, top = 0, bottom = 0 } = props.viewportInsets
  camera.setViewOffset(size.width, size.height, (right - left) / 2, (bottom - top) / 2, size.width, size.height)
  camera.updateProjectionMatrix(); controls.update()
  syncPanelTop()
}
function zoom(factor) { if (camera) { camera.zoom = THREE.MathUtils.clamp(camera.zoom * factor, .45, 5); camera.updateProjectionMatrix(); captureCamera(); syncPanelTop() } }
function pointerDown(event) { if (event.button === 0) down = { x: event.clientX, y: event.clientY } }
function pointerUp(event) {
  if (!down || Math.hypot(event.clientX - down.x, event.clientY - down.y) > 5) { down = null; return }
  down = null
  const rect = renderer.domElement.getBoundingClientRect()
  raycaster.setFromCamera(new THREE.Vector2((event.clientX - rect.left) / rect.width * 2 - 1, -(event.clientY - rect.top) / rect.height * 2 + 1), camera)
  const hit = raycaster.intersectObjects(selectable, true)[0]
  let object = hit?.object
  while (object && !object.userData.dispatchWaypoint) object = object.parent
  if (object) choose(object.userData.dispatchWaypoint)
}
function pointerCancel() { down = null }
onMounted(async () => {
  try {
    scene = new THREE.Scene(); scene.background = null
    camera = new THREE.OrthographicCamera(-20, 20, 16, -16, .1, 250)
    renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true })
    renderer.setClearColor(0x000000, 0); renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
    renderer.outputColorSpace = THREE.SRGBColorSpace
    renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1
    host.value.prepend(renderer.domElement)
    controls = new MapControls(camera, renderer.domElement)
    controls.enableRotate = false; controls.enableDamping = true; controls.dampingFactor = .1
    controls.screenSpacePanning = true; controls.minZoom = .45; controls.maxZoom = 5
    controls.mouseButtons.LEFT = THREE.MOUSE.PAN; controls.mouseButtons.RIGHT = THREE.MOUSE.PAN
    scene.add(new THREE.HemisphereLight(0xffffff, 0x72808d, 1.5))
    const key = new THREE.DirectionalLight(0xffffff, 2.1); key.position.set(-12, 30, 18); scene.add(key)
    mapRoot = new THREE.Group(); scene.add(mapRoot)
    routeLayer = new THREE.Group(); mapRoot.add(routeLayer)
    overlay = new THREE.Group(); mapRoot.add(overlay)
    if (debugEnabled) controls.addEventListener('change', captureCamera)
    observer = new ResizeObserver(resize); observer.observe(host.value); resize()
    const canvas = renderer.domElement
    canvas.addEventListener('pointerdown', pointerDown); canvas.addEventListener('pointerup', pointerUp); canvas.addEventListener('pointercancel', pointerCancel)
    const animate = () => { if (disposed) return; frame = requestAnimationFrame(animate); controls.update(); projectMarkers(); renderer.render(scene, camera) }
    frame = requestAnimationFrame(animate)
    const graphPromise = fetch(NAVIGATION_ASSETS.graph0, { signal: abort.signal, cache: 'no-cache' }).then(async (response) => {
      if (!response.ok) throw new Error('graph')
      const buffer = await response.arrayBuffer()
      return { data: JSON.parse(new TextDecoder().decode(buffer)), hash: await sha256Hex(buffer) }
    })
    const mappingPromise = fetch(NAVIGATION_ASSETS.dispatchRouteMapping, { signal: abort.signal, cache: 'no-cache' }).then(async (response) => {
      if (!response.ok) throw new Error('mapping')
      return response.json()
    })
    const response = await fetch(runtimeModelUrl(SCENE_ASSETS.dispatchFloor), { signal: abort.signal, cache: 'no-cache' })
    if (!response.ok) throw new Error(`模型載入失敗 (${response.status})`)
    const glbBuffer = await readModelResponse(response, (progress) => { if (!disposed) modelProgress.value = progress })
    const gltf = await createGltfLoader().parseAsync(glbBuffer, '')
    modelScenes = gltf.scenes
    if (disposed) { modelScenes.forEach(disposeObject); resources.forEach((resource) => resource.dispose()); resources.clear(); return }
    model = gltf.scene
    const excluded = []; model.traverse((object) => { if (isDispatchPreview(object)) excluded.push(object) })
    excluded.forEach((object) => { disposeObject(object); object.removeFromParent() })
    model.updateMatrixWorld(true)
    const byName = new Map(); model.traverse((object) => {
      const name = modelObjectName(object)
      byName.set(name, object)
      if (/^Route(?:Node)?_/.test(name)) object.visible = false
    })
    for (const [name, entry] of Object.entries(dispatchLocations)) {
      const room = byName.get(`Room_${entry.room}`)
      if (room) { room.userData.dispatchWaypoint = name; selectable.push(room) }
    }
    mapRoot.add(model)
    const roomBounds = new THREE.Box3()
    for (const [name, object] of byName) if (name.startsWith('Room_')) roomBounds.union(new THREE.Box3().setFromObject(object))
    roomVisualBounds = roomBounds.clone()
    const roomCenter = roomBounds.getCenter(new THREE.Vector3()); roomCenter.y = 0
    // Use the space immediately below the navbar; keep the model clear of it.
    roomCenter.z += .45
    const roomSize = roomBounds.getSize(new THREE.Vector3())
    viewSpan = Math.max(25, roomSize.z * 1.2, roomSize.x * 1.16 / Math.max(size.width / size.height, .5))
    const [{ data: graphData, hash: graphHash }, mapData, glbHash] = await Promise.all([graphPromise, mappingPromise, sha256Hex(glbBuffer)])
    if (!disposed) {
      const graphSource = 'frontend/public/generated/rmf-navigation.json'
      const modelSource = 'frontend/public/models/L1__flat.glb'
      // The runtime loads the Draco copy, so check it against the manifest and the manifest's
      // recorded source hash against the mapping (which is generated from the source GLB).
      const compressed = COMPRESSED_MODELS['L1__flat.glb']
      const mappedModelHash = mapData.source?.[modelSource] || ''
      const modelMatches = mappedModelHash === glbHash
        || (!!compressed && glbHash.startsWith(compressed.version) && mappedModelHash.startsWith(compressed.source))
      if (mapData.source?.[graphSource] !== graphHash || !modelMatches || !validateDispatchMapping(mapData, graphData)) {
        graphError.value = '路線對應資料與目前導航圖或 GLB 版本不符，請重新產生對應資料。'
      } else {
        graph.value = graphData; mapping.value = mapData
        drawRouteNetwork(mapData); updateOverlay()
      }
    }
    applyModelPreset()
    factoryTarget = mapRoot.localToWorld(roomCenter.clone())
    factoryPosition = factoryTarget.clone().add(new THREE.Vector3(0, 48, 27))
    const savedCamera = readDispatchCameraPreset()
    defaultTarget = savedCamera ? new THREE.Vector3(savedCamera.target.x, savedCamera.target.y, savedCamera.target.z) : factoryTarget.clone()
    defaultPosition = savedCamera ? new THREE.Vector3(savedCamera.position.x, savedCamera.position.y, savedCamera.position.z) : factoryPosition.clone()
    defaultZoom = savedCamera?.zoom || FACTORY_DISPATCH_ZOOM
    resize(); resetView(); controls.saveState(); captureCamera(); loading.value = false; syncPanelTop()
  } catch (reason) { if (!disposed) { loading.value = false; error.value = `無法載入樓層模型：${reason.message}` } }
})
watch(modelPreset, applyModelPreset, { deep: true })
watch(() => props.viewportInsets, resize, { deep: true })
watch(() => [props.robots, props.source, props.destination, props.routeConfirmed], updateOverlay, { deep: true })
onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', onFloorPickerOutside)
  disposed = true; abort.abort(); cancelAnimationFrame(frame); observer?.disconnect()
  const canvas = renderer?.domElement
  canvas?.removeEventListener('pointerdown', pointerDown); canvas?.removeEventListener('pointerup', pointerUp); canvas?.removeEventListener('pointercancel', pointerCancel)
  controls?.removeEventListener('change', captureCamera); controls?.dispose(); clearOverlay(); clearGroup(routeLayer); modelScenes.forEach(disposeObject)
  resources.forEach((resource) => resource.dispose()); resources.clear(); scene?.clear()
  renderer?.dispose(); renderer?.forceContextLoss(); canvas?.remove()
})
</script>

<template>
  <section ref="host" class="dispatch-scene" :style="mapStyle" :aria-label="`F1 ${t('map.title')}`">
    <nav class="dispatch-map-toolbar" :aria-label="t('map.title')">
      <div ref="floorPicker" class="dispatch-floor-picker" @mouseenter="floorPickerOpen=true" @mouseleave="floorPickerOpen=false" @keydown.esc.stop="floorPickerOpen=false"><button type="button" class="dispatch-floor-trigger" :aria-label="t('map.selectFloor')" :aria-expanded="floorPickerOpen" aria-haspopup="listbox" @click="floorPickerOpen=!floorPickerOpen">F{{ activeFloor }}</button><div v-if="floorPickerOpen" class="dispatch-floor-options" role="listbox" :aria-label="t('map.selectFloor')"><button v-for="floor in dispatchFloors" :key="floor.id" type="button" role="option" :aria-selected="activeFloor===floor.id" @click="selectFloor(floor)">{{ floor.label }}</button></div></div>
      <div class="dispatch-map-controls"><button type="button" :aria-label="t('map.zoomIn')" :title="t('map.zoomIn')" @click="zoom(1.2)">＋</button><button type="button" :aria-label="t('map.zoomOut')" :title="t('map.zoomOut')" @click="zoom(1 / 1.2)">－</button><button type="button" :aria-label="t('map.reset')" :title="t('map.reset')" @click="resetView"><RotateCcw :size="13" /></button></div>
    </nav>
    <p v-if="activeFloor !== 1" class="dispatch-floor-preview-note" role="status">{{ t('map.f1Preview') }}</p>
    <div class="dispatch-marker-layer">
      <button v-for="marker in markers" v-show="marker.visible && !loading" :key="marker.name" type="button" class="dispatch-station" :class="{ 'is-source': marker.source, 'is-destination': marker.destination }" :style="{ left: `${marker.x}px`, top: `${marker.y}px` }" :data-waypoint="marker.name" :aria-label="t('map.selectLocation', { name: translateLocation(marker.label) })" :title="translateLocation(marker.label)" @click="choose(marker.name)"><svg v-if="marker.source || marker.destination" class="station-pin" viewBox="0 0 32 44" aria-hidden="true"><path d="M16 1C7.7 1 1 7.7 1 16c0 11.2 15 27 15 27s15-15.8 15-27C31 7.7 24.3 1 16 1Z"/><circle cx="16" cy="16" r="6"/></svg><span v-else class="station-dot"></span><span v-if="marker.source || marker.destination" class="station-label">{{ marker.source ? t('dispatchForm.source') : t('dispatchForm.destination') }} · {{ translateLocation(marker.label) }}</span></button>
      <div v-for="robot in robotMarkers" v-show="robot.visible" :key="robot.id" class="dispatch-robot" :style="{ left: `${robot.x}px`, top: `${robot.y}px`, '--robot-color': robot.color }" :title="robot.displayCode"><i>⌃</i><span>{{ robot.displayCode }}</span></div>
    </div>
    <SharedLoading :loading="loading" :detail="modelProgress === null ? t('map.loadingModel') : `${modelProgress}%`" />
    <div v-if="error" class="dispatch-map-message" role="alert">{{ error }}</div>
    <p v-if="graphError" class="dispatch-map-error" role="alert">{{ graphError }}</p>
    <aside v-if="debugEnabled" class="dispatch-debug-panel" :aria-label="t('dispatchDebug.title')">
      <header><strong>{{ t('dispatchDebug.title') }}</strong><small>{{ debugStatus }}</small></header>
      <p>{{ t('dispatchDebug.hint') }}</p>
      <fieldset v-if="cameraDebugEnabled"><legend>{{ t('dispatchDebug.camera') }}</legend><label>{{ t('dispatchDebug.position') }} X<input v-model.number="cameraPreset.position.x" type="number" step="0.1" @change="applyCameraPreset"></label><label>{{ t('dispatchDebug.position') }} Y<input v-model.number="cameraPreset.position.y" type="number" step="0.1" @change="applyCameraPreset"></label><label>{{ t('dispatchDebug.position') }} Z<input v-model.number="cameraPreset.position.z" type="number" step="0.1" @change="applyCameraPreset"></label><label>{{ t('dispatchDebug.target') }} X<input v-model.number="cameraPreset.target.x" type="number" step="0.1" @change="applyCameraPreset"></label><label>{{ t('dispatchDebug.target') }} Y<input v-model.number="cameraPreset.target.y" type="number" step="0.1" @change="applyCameraPreset"></label><label>{{ t('dispatchDebug.target') }} Z<input v-model.number="cameraPreset.target.z" type="number" step="0.1" @change="applyCameraPreset"></label><label>{{ t('dispatchDebug.zoom') }}<input v-model.number="cameraPreset.zoom" type="number" min="0.45" max="5" step="0.1" @change="applyCameraPreset"></label></fieldset>
      <fieldset v-if="modelDebugEnabled"><legend>{{ t('dispatchDebug.model') }}</legend><label>{{ t('dispatchDebug.offset') }} X<input v-model.number="modelPreset.position.x" type="number" step="0.1"></label><label>{{ t('dispatchDebug.offset') }} Y<input v-model.number="modelPreset.position.y" type="number" step="0.1"></label><label>{{ t('dispatchDebug.offset') }} Z<input v-model.number="modelPreset.position.z" type="number" step="0.1"></label><label>{{ t('dispatchDebug.rotation') }}<input :value="Math.round(modelPreset.rotationY * 180 / Math.PI * 10) / 10" type="number" step="1" @change="modelPreset.rotationY = Number($event.target.value) * Math.PI / 180"></label><label>{{ t('dispatchDebug.scale') }}<input v-model.number="modelPreset.scale" type="number" min="0.5" max="2" step="0.05"></label></fieldset>
      <footer><button type="button" @click="copyDebugPreset">{{ t('dispatchDebug.copy') }}</button><button type="button" @click="resetDebugPreset">{{ t('dispatchDebug.factory') }}</button><button type="button" @click="saveDebugPreset">{{ t('dispatchDebug.save') }}</button></footer>
    </aside>
  </section>
</template>

<style scoped>
.dispatch-scene{position:relative;width:100%;height:100%;min-height:0;overflow:hidden;background:transparent}.dispatch-scene :deep(canvas){display:block;width:100%;height:100%;touch-action:none;cursor:grab}.dispatch-scene :deep(canvas:active){cursor:grabbing}.dispatch-map-controls{position:absolute;z-index:4;top:24px;right:var(--safe-right);display:flex;gap:6px}.dispatch-map-controls button{height:34px;min-width:34px;padding:0 10px;color:var(--text-primary);font-size:12px;background:var(--surface-glass);border:1px solid var(--glass-border);border-radius:7px;backdrop-filter:blur(14px);cursor:pointer}.dispatch-map-controls button:hover{background:var(--surface-glass-strong)}.dispatch-marker-layer{position:absolute;inset:0;pointer-events:none}.dispatch-station{position:absolute;display:flex;align-items:center;justify-content:center;width:26px;height:26px;padding:0;border:0;background:none;transform:translate(-50%,-50%);pointer-events:auto;cursor:pointer}.station-dot{width:9px;height:9px;border:2px solid #fff;border-radius:50%;background:#397f56;box-shadow:0 1px 4px #263b4333}.is-source .station-dot,.is-destination .station-dot{width:12px;height:12px;background:#f49466;box-shadow:0 0 0 4px #f4946638}.is-source .station-dot{background:#fff;border-color:#f49466}.station-label,.station-robots{position:absolute;top:26px;left:50%;padding:4px 7px;border-radius:5px;transform:translateX(-50%);white-space:nowrap;font-size:10px;color:var(--text-primary);background:var(--surface-glass-strong);backdrop-filter:blur(10px)}.station-robots{top:auto;bottom:25px;color:#365565}.dispatch-map-message{position:absolute;inset:0;display:grid;place-items:center;pointer-events:none;font-size:13px;color:var(--text-secondary)}.dispatch-alignment-note{position:absolute;bottom:26px;left:var(--safe-left);right:var(--safe-right);margin:0;color:var(--text-secondary);font-size:10px;text-align:center;pointer-events:none}.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%)}button:focus-visible{outline:2px solid var(--theme-primary);outline-offset:3px}
@media(max-width:1179px){.dispatch-map-controls{right:16px;top:16px}.dispatch-alignment-note{left:16px;right:16px}}
.dispatch-robot{position:absolute;display:grid;justify-items:center;gap:2px;transform:translate(-50%,-100%);pointer-events:none;font-size:9px;color:#34414b}.dispatch-robot i{display:grid;place-items:center;width:19px;height:19px;border:2px solid white;border-radius:6px;background:var(--robot-color);font-size:16px;font-style:normal;box-shadow:0 2px 7px #34414b30}
.dispatch-map-toolbar{position:absolute;z-index:6;top:10px;right:10px;display:flex;align-items:center;gap:4px}.dispatch-map-controls{position:relative;top:auto;right:auto;flex-direction:row;gap:4px}.dispatch-map-controls button{display:grid;place-items:center;width:30px;min-width:30px;height:30px;padding:0;font-size:17px}.dispatch-floor-picker{position:relative;display:flex;align-items:center;width:48px;height:30px}.dispatch-floor-trigger{display:flex;align-items:center;justify-content:space-between;width:100%;height:100%;padding:0 7px;color:var(--text-primary);font:inherit;font-size:11px;font-weight:600;background:var(--surface-glass);border:1px solid var(--glass-border);border-radius:7px;backdrop-filter:blur(14px);cursor:pointer}.dispatch-floor-trigger svg{flex:none;color:var(--text-secondary)}.dispatch-floor-options{position:absolute;top:calc(100% + 4px);right:0;display:grid;gap:2px;min-width:64px;padding:4px;background:#f8faf9;border:1px solid var(--panel-border);border-radius:8px;box-shadow:0 10px 22px #34433825;backdrop-filter:blur(18px)}.dispatch-floor-options button{min-height:26px;padding:4px 7px;color:var(--text-primary);background:transparent;border:0;border-radius:5px;font:inherit;font-size:11px;text-align:left;cursor:pointer}.dispatch-floor-options button:hover,.dispatch-floor-options button[aria-selected=true]{background:color-mix(in srgb,#fb9966 15%,transparent)}.dispatch-floor-trigger:focus-visible,.dispatch-floor-options button:focus-visible{outline:2px solid var(--theme-primary);outline-offset:1px}:global([data-theme=dark]) .dispatch-floor-options{background:#303735}.dispatch-floor-preview-note{position:absolute;z-index:4;top:47px;right:10px;margin:0;padding:5px 8px;color:var(--text-secondary);font-size:10px;white-space:nowrap;background:var(--surface-glass-strong);border:1px solid var(--glass-border);border-radius:6px;backdrop-filter:blur(12px);pointer-events:none}.station-dot{background:#e98b4b}.is-source .station-dot,.is-destination .station-dot{background:#33a475}.is-source .station-dot{border-color:white}.dispatch-map-error{position:absolute;bottom:12px;left:12px;margin:0;color:var(--text-secondary);font-size:11px}
.dispatch-debug-panel{position:absolute;z-index:8;top:12px;left:12px;width:260px;max-height:calc(100% - 24px);box-sizing:border-box;overflow:auto;padding:12px;color:var(--text-primary);background:var(--surface-glass-strong);border:1px solid var(--glass-border);border-radius:9px;box-shadow:0 8px 26px #34433820;backdrop-filter:blur(18px)}.dispatch-debug-panel header{display:grid;gap:3px}.dispatch-debug-panel header strong{font-size:13px}.dispatch-debug-panel header small{font-size:10px;color:var(--theme-primary)}.dispatch-debug-panel p{font-size:10px;line-height:1.5;color:var(--text-secondary)}.dispatch-debug-panel fieldset{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:5px;margin:8px 0;padding:7px;border:1px solid var(--glass-border);border-radius:6px}.dispatch-debug-panel legend{padding:0 3px;font-size:11px}.dispatch-debug-panel label{display:grid;gap:2px;min-width:0;font-size:10px;color:var(--text-secondary)}.dispatch-debug-panel input{box-sizing:border-box;width:100%;min-width:0;height:27px;padding:2px 5px;color:var(--text-primary);background:var(--surface-glass);border:1px solid var(--glass-border);border-radius:4px}.dispatch-debug-panel footer{display:flex;flex-wrap:wrap;gap:4px}.dispatch-debug-panel footer button{padding:5px 7px;color:var(--text-primary);background:var(--surface-glass);border:1px solid var(--glass-border);border-radius:5px;font-size:10px;cursor:pointer}
.dispatch-station.is-source,.dispatch-station.is-destination{z-index:2;width:42px;height:52px;transform:translate(-50%,-100%)}.station-pin{display:block;flex:none;align-self:flex-end;width:32px;height:44px;overflow:visible;filter:drop-shadow(0 3px 4px #34414b65)}.station-pin path{stroke-width:1.4}.dispatch-station.is-source .station-pin path{fill:#e85a55;stroke:#a93537}.dispatch-station.is-destination .station-pin path{fill:#2789ae;stroke:#165b78}.station-pin circle{fill:#fff}.dispatch-station.is-source .station-label,.dispatch-station.is-destination .station-label{top:calc(100% + 2px)}
.dispatch-map-toolbar{top:12px;right:12px;display:grid;justify-items:center;gap:2px;width:44px;padding:4px;box-sizing:border-box;background:var(--info-background);border:var(--info-border);border-radius:var(--info-radius);box-shadow:var(--info-shadow);backdrop-filter:var(--info-backdrop);-webkit-backdrop-filter:var(--info-backdrop);transform:none}
.dispatch-map-controls{display:grid;justify-items:center;gap:2px;width:100%}
.dispatch-map-controls button,.dispatch-floor-picker{width:34px;height:34px}
.dispatch-map-controls button{min-width:34px;color:var(--text-muted);background:transparent;border:0;border-radius:var(--radius-control);box-shadow:none;backdrop-filter:none;font-size:20px;font-weight:300;line-height:1}
.dispatch-map-controls button:hover,.dispatch-floor-trigger:hover{color:var(--theme-primary);background:var(--theme-primary-soft)}
.dispatch-map-controls button svg{width:15px;height:15px;stroke-width:1.7}
.dispatch-floor-trigger{justify-content:center;padding:0;color:var(--theme-primary);background:transparent;border:0;border-radius:var(--radius-control);backdrop-filter:none;font-size:13px;font-weight:400}
.dispatch-floor-options{top:0;right:calc(100% + 8px);min-width:72px}
.dispatch-floor-options::after{position:absolute;top:0;right:-8px;width:8px;height:100%;content:''}
.dispatch-floor-preview-note{top:12px;right:64px}
</style>
