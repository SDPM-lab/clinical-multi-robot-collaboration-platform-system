<script setup>
import { nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { clone as cloneScene } from 'three/addons/utils/SkeletonUtils.js'
import { RotateCcw } from '@lucide/vue'
import { AgibotArmAssembly } from '@/three/robot/AgibotArmAssembly.js'
import { DEFAULT_ROBOT_ASSET, loadRobotAsset } from '@/three/robot/robotModelAssets.js'
import { defaultRobotModelPreset, readRobotCameraPreset, readRobotModelPreset, storeRobotCameraPreset, storeRobotModelPreset, validRobotCameraPreset, validRobotModelPreset } from '@/config/robotViewportPreset.js'
import { t } from '@/i18n/index.js'
import SharedLoading from '@/components/SharedLoading.vue'

const params = new URLSearchParams(window.location.search)
const robotDebugEnabled = params.get('robotDebug') === '1'
const cameraDebugEnabled = robotDebugEnabled && params.get('cameraDebug') === '1'
const modelDebugEnabled = robotDebugEnabled && params.get('modelDebug') === '1'
const debugEnabled = cameraDebugEnabled || modelDebugEnabled
const props = defineProps({ robotId: String, modelAssetKey: { type: String, default: DEFAULT_ROBOT_ASSET } })
const emit = defineEmits(['ready'])
const host = ref(null)
const loading = ref(true)
const error = ref('')
const debugStatus = ref('')
const cameraPreset = reactive({ position: { x: 0, y: 0, z: 0 }, target: { x: 0, y: 0, z: 0 }, fov: 35, aspect: 1 })
const modelPreset = reactive(readRobotModelPreset() || defaultRobotModelPreset())
let renderer, scene, camera, controls, observer, assembly, model, frame
let disposed = false
let loadToken = 0
let zoneAmounts = { l: 0, r: 0, head: 0, base: 0 }
let activeZone = null
let cameraTween = null
let lastFrame = 0
let viewportWidth = 0
let viewportHeight = 0
const frontDirection = new THREE.Vector3(1, .13, .28).normalize()
const rounded = value => Math.round(value * 1000) / 1000

function staticAssembly(root) {
  const bounds = new THREE.Box3().setFromObject(root)
  return {
    assembledBounds: bounds,
    explodedBounds: bounds.clone(),
    set() {},
    setZones() {},
    zoneBounds: () => new THREE.Box3(),
    boundsAt: () => bounds.clone(),
  }
}

function captureCamera() {
  if (!camera || !controls || !debugEnabled) return
  for (const axis of ['x', 'y', 'z']) {
    cameraPreset.position[axis] = rounded(camera.position[axis])
    cameraPreset.target[axis] = rounded(controls.target[axis])
  }
  cameraPreset.fov = rounded(camera.fov)
  cameraPreset.aspect = camera.aspect
}

function applyCameraPreset(preset = cameraPreset, boundsOverride) {
  if (!camera || !controls || !validRobotCameraPreset(preset)) { debugStatus.value = t('robotDebug.invalid'); return }
  camera.position.set(Number(preset.position.x), Number(preset.position.y), Number(preset.position.z))
  controls.target.set(Number(preset.target.x), Number(preset.target.y), Number(preset.target.z))
  camera.fov = Number(preset.fov)
  camera.updateProjectionMatrix()
  if (assembly && preset.aspect) {
    const direction = camera.position.clone().sub(controls.target).normalize()
    const bounds = boundsOverride || viewBounds()
    const sourceFit = fitDistance(bounds, direction, Number(preset.aspect))
    const currentFit = fitDistance(bounds, direction)
    camera.position.sub(controls.target).multiplyScalar(currentFit / sourceFit).add(controls.target)
  }
  controls.update()
  debugStatus.value = ''
}

function applyModelPreset() {
  if (!model || !validRobotModelPreset(modelPreset)) { debugStatus.value = t('robotDebug.invalid'); return }
  model.position.set(Number(modelPreset.position.x), Number(modelPreset.position.y), Number(modelPreset.position.z))
  model.rotation.y = Number(modelPreset.rotationY)
  model.scale.setScalar(Number(modelPreset.scale))
  model.updateMatrixWorld(true)
  if (assembly) {
    assembly.set(0)
    assembly.assembledBounds.setFromObject(model)
    assembly.set(1)
    assembly.explodedBounds.setFromObject(model)
    assembly.setZones(zoneAmounts)
    resize()
  }
  debugStatus.value = ''
}

function saveDebugPreset() {
  captureCamera()
  if (!validRobotCameraPreset(cameraPreset) || !validRobotModelPreset(modelPreset)) { debugStatus.value = t('robotDebug.invalid'); return }
  try {
    storeRobotCameraPreset(cameraPreset)
    storeRobotModelPreset(modelPreset)
    debugStatus.value = t('robotDebug.saved')
  } catch { debugStatus.value = t('robotDebug.saveFailed') }
}

function factoryDebugPreset() {
  Object.assign(modelPreset, defaultRobotModelPreset())
  applyModelPreset()
  fitFactoryView()
  captureCamera()
  debugStatus.value = t('robotDebug.reset')
}

async function copyDebugPreset() {
  captureCamera()
  try {
    await navigator.clipboard.writeText(JSON.stringify({ camera: cameraPreset, model: modelPreset }, null, 2))
    debugStatus.value = t('robotDebug.copied')
  } catch { debugStatus.value = t('robotDebug.copyFailed') }
}

function fitDistance(bounds, direction, aspect = camera.aspect) {
  const center = bounds.getCenter(new THREE.Vector3())
  const right = new THREE.Vector3().crossVectors(camera.up, direction).normalize()
  const up = new THREE.Vector3().crossVectors(direction, right).normalize()
  const tanY = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) * .68
  const tanX = tanY * aspect
  let distance = 0
  for (const x of [bounds.min.x, bounds.max.x])
    for (const y of [bounds.min.y, bounds.max.y])
      for (const z of [bounds.min.z, bounds.max.z]) {
        const point = new THREE.Vector3(x, y, z).sub(center)
        distance = Math.max(distance,
          point.dot(direction) + Math.abs(point.dot(right)) / tanX,
          point.dot(direction) + Math.abs(point.dot(up)) / tanY)
      }
  return Math.max(distance, camera.near * 4)
}

function viewBounds() {
  return activeZone ? assembly.zoneBounds(activeZone) : assembly.boundsAt(Math.max(...Object.values(zoneAmounts)))
}

function fitFactoryView() {
  if (!assembly || !camera || !controls) return
  camera.fov = 35
  camera.updateProjectionMatrix()
  const bounds = assembly.assembledBounds
  const target = bounds.getCenter(new THREE.Vector3())
  const distance = fitDistance(bounds, frontDirection)
  controls.target.copy(target)
  camera.position.copy(target).addScaledVector(frontDirection, distance)
  controls.minDistance = Math.max(.55, assembly.assembledBounds.getSize(new THREE.Vector3()).length() * .32)
  controls.maxDistance = Math.max(distance * 3, 12)
  camera.near = Math.max(.01, controls.minDistance * .02)
  camera.far = Math.max(100, controls.maxDistance * 3)
  camera.updateProjectionMatrix()
  controls.update()
}

function resetView() {
  fitFactoryView()
  const saved = readRobotCameraPreset()
  if (saved && props.modelAssetKey === DEFAULT_ROBOT_ASSET) applyCameraPreset(saved, assembly.assembledBounds)
  captureCamera()
}

function moveCameraTo(position, target) {
  cameraTween = {
    fromPosition: camera.position.clone(),
    fromTarget: controls.target.clone(),
    toPosition: position.clone(),
    toTarget: target.clone(),
    startTime: performance.now(),
  }
  controls.enabled = false
}

function focusZone(zone) {
  if (!assembly || !controls || !['l', 'r', 'head', 'base'].includes(zone)) return
  activeZone = zone
  assembly.setZones({ [zone]: 1 })
  const bounds = assembly.zoneBounds(zone)
  assembly.setZones(zoneAmounts)
  if (bounds.isEmpty()) return
  const target = bounds.getCenter(new THREE.Vector3())
  if (zone === 'head') {
    const right = new THREE.Vector3().crossVectors(camera.up, frontDirection).normalize()
    const screenUp = new THREE.Vector3().crossVectors(frontDirection, right).normalize()
    const offset = Math.max(.1, Math.min(.22, bounds.getSize(new THREE.Vector3()).length() * .18))
    target.addScaledVector(screenUp, -offset)
  }
  const distance = fitDistance(bounds, frontDirection) * .85
  controls.minDistance = Math.max(.12, bounds.getSize(new THREE.Vector3()).length() * .18)
  controls.maxDistance = Math.max(distance * 3, 12)
  camera.near = Math.max(.005, controls.minDistance * .02)
  camera.far = Math.max(100, controls.maxDistance * 3)
  camera.updateProjectionMatrix()
  moveCameraTo(target.clone().addScaledVector(frontDirection, distance), target)
}

function focusArm(side) { focusZone(side) }

function showWholeRobot() {
  if (!assembly || !controls) return
  activeZone = null
  const fromPosition = camera.position.clone()
  const fromTarget = controls.target.clone()
  resetView()
  const toPosition = camera.position.clone()
  const toTarget = controls.target.clone()
  camera.position.copy(fromPosition)
  controls.target.copy(fromTarget)
  controls.update()
  moveCameraTo(toPosition, toTarget)
}

function resize() {
  if (!host.value || !renderer || !camera) return
  const { width, height } = host.value.getBoundingClientRect()
  if (width < 1 || height < 1) return
  const sizeChanged = width !== viewportWidth || height !== viewportHeight
  const bounds = assembly && viewBounds()
  const direction = controls && camera.position.clone().sub(controls.target).normalize()
  const previousFit = bounds && direction && viewportWidth && viewportHeight && sizeChanged
    ? fitDistance(bounds, direction)
    : 0
  renderer.setSize(width, height, false)
  camera.aspect = width / height
  camera.updateProjectionMatrix()
  viewportWidth = width
  viewportHeight = height
  if (!assembly || !controls || !sizeChanged) return
  const needed = fitDistance(bounds, direction)
  const distance = camera.position.distanceTo(controls.target)
  // Preserve the user's zoom across fullscreen and other container resizes.
  const nextDistance = previousFit
    ? distance * needed / previousFit
    : distance
  if (nextDistance !== distance) camera.position.copy(controls.target).addScaledVector(direction, nextDistance)
  controls.update()
  if (sizeChanged) captureCamera()
}

function animate(time) {
  if (disposed) return
  frame = requestAnimationFrame(animate)
  const delta = lastFrame ? Math.min((time - lastFrame) / 1000, .05) : 0
  lastFrame = time
  if (document.hidden || !assembly) return
  let assemblyChanged = false
  for (const zone of ['l', 'r', 'head', 'base']) {
    const target = activeZone === zone ? 1 : 0
    if (zoneAmounts[zone] === target) continue
    zoneAmounts[zone] = Math.abs(zoneAmounts[zone] - target) < .0005
      ? target
      : THREE.MathUtils.lerp(zoneAmounts[zone], target, 1 - Math.exp(-9 * delta))
    assemblyChanged = true
  }
  if (assemblyChanged) assembly.setZones(zoneAmounts)
  if (cameraTween) {
    const progress = Math.min(1, (time - cameraTween.startTime) / 650)
    const eased = 1 - Math.pow(1 - progress, 3)
    camera.position.copy(cameraTween.fromPosition).lerp(cameraTween.toPosition, eased)
    controls.target.copy(cameraTween.fromTarget).lerp(cameraTween.toTarget, eased)
    if (progress >= 1) {
      cameraTween = null
      controls.enabled = true
      captureCamera()
    }
  }
  controls.update()
  renderer.render(scene, camera)
}

function initializeRenderer() {
  if (renderer) return
  renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
  renderer.setClearColor(0x000000, 0)
  renderer.outputColorSpace = THREE.SRGBColorSpace
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 1
  host.value.prepend(renderer.domElement)
  scene = new THREE.Scene()
  camera = new THREE.PerspectiveCamera(35, 1, .01, 100)
  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = .07
  controls.enablePan = true
  controls.minPolarAngle = .12
  controls.maxPolarAngle = Math.PI - .12
  if (debugEnabled) controls.addEventListener('end', captureCamera)
  scene.add(new THREE.HemisphereLight(0xf7f9ff, 0x555c65, 1.35))
  const key = new THREE.DirectionalLight(0xffffff, 2.2)
  key.position.set(3, 5, 4)
  const fill = new THREE.DirectionalLight(0xe4ecff, .85)
  fill.position.set(-2, 2, -4)
  scene.add(key, fill)
  observer = new ResizeObserver(resize)
  observer.observe(host.value)
  resize()
}

async function start() {
  const token = ++loadToken
  loading.value = true
  error.value = ''
  try {
    initializeRenderer()
    if (model) scene.remove(model)
    model = null
    assembly = null
    const asset = await loadRobotAsset(props.modelAssetKey)
    if (disposed || token !== loadToken) return
    if (props.modelAssetKey === DEFAULT_ROBOT_ASSET && !asset.scene.getObjectByName('AGIBOT_A2D')) throw new Error('AGIBOT_A2D root node missing')
    model = cloneScene(asset.scene)
    scene.add(model)
    if (props.modelAssetKey === DEFAULT_ROBOT_ASSET) applyModelPreset()
    let structureAvailable = false
    if (model.getObjectByName('AGIBOT_A2D')) {
      try {
        assembly = new AgibotArmAssembly(model)
        structureAvailable = assembly.records.length > 0
      } catch (reason) {
        if (props.modelAssetKey === DEFAULT_ROBOT_ASSET) throw reason
      }
    }
    if (!assembly) assembly = staticAssembly(model)
    zoneAmounts = { l: 0, r: 0, head: 0, base: 0 }
    activeZone = null
    resize()
    resetView()
    loading.value = false
    emit('ready', { structureAvailable })
    await nextTick()
    if (disposed || token !== loadToken) return
    resize()
    resetView()
    if (!frame) frame = requestAnimationFrame(animate)
  } catch (reason) {
    if (disposed || token !== loadToken) return
    loading.value = false
    error.value = 'loadError'
    console.error(reason)
  }
}

watch(() => [props.robotId, props.modelAssetKey], ([, assetKey], [, previousAssetKey]) => {
  zoneAmounts = { l: 0, r: 0, head: 0, base: 0 }
  activeZone = null
  cameraTween = null
  if (controls) controls.enabled = true
  assembly?.set(0)
  if (assetKey !== previousAssetKey) start()
  else resetView()
})
onMounted(start)
onBeforeUnmount(() => {
  disposed = true
  loadToken++
  cancelAnimationFrame(frame)
  observer?.disconnect()
  if (debugEnabled) controls?.removeEventListener('end', captureCamera)
  controls?.dispose()
  if (model) scene?.remove(model)
  renderer?.forceContextLoss()
  renderer?.dispose()
  renderer?.domElement.remove()
})
defineExpose({ focusArm, focusZone, showWholeRobot, resetView })
</script>

<template>
  <div ref="host" class="robot-viewport" :aria-label="t('robotStatus.modelView')">
    <SharedLoading :loading="loading" />
    <div v-if="!loading && error" class="viewport-message" role="alert">{{ t(props.modelAssetKey === DEFAULT_ROBOT_ASSET ? 'robotStatus.loadError' : 'robotStatus.customLoadError') }}<button type="button" @click="start">{{ t('robotStatus.retry') }}</button></div>
    <div v-else-if="!loading" class="viewport-controls">
      <button type="button" class="viewport-reset" :aria-label="t('robotStatus.resetView')" :title="t('robotStatus.resetView')" @click="showWholeRobot"><RotateCcw :size="17" aria-hidden="true"/></button>
    </div>
    <details v-if="debugEnabled && !loading && !error" class="robot-debug-panel" open>
      <summary>{{ t('robotDebug.title') }}<span>{{ debugStatus }}</span></summary>
      <p>{{ t('robotDebug.hint') }}</p>
      <fieldset v-if="cameraDebugEnabled">
        <legend>{{ t('robotDebug.camera') }}</legend>
        <label v-for="axis in ['x', 'y', 'z']" :key="`camera-${axis}`">{{ t('robotDebug.position') }} {{ axis.toUpperCase() }}<input v-model.number="cameraPreset.position[axis]" type="number" step="0.05" @change="applyCameraPreset()"></label>
        <label v-for="axis in ['x', 'y', 'z']" :key="`target-${axis}`">{{ t('robotDebug.target') }} {{ axis.toUpperCase() }}<input v-model.number="cameraPreset.target[axis]" type="number" step="0.05" @change="applyCameraPreset()"></label>
        <label>{{ t('robotDebug.fov') }}<input v-model.number="cameraPreset.fov" type="number" min="20" max="70" step="1" @change="applyCameraPreset()"></label>
      </fieldset>
      <fieldset v-if="modelDebugEnabled">
        <legend>{{ t('robotDebug.model') }}</legend>
        <label v-for="axis in ['x', 'y', 'z']" :key="`model-${axis}`">{{ t('robotDebug.offset') }} {{ axis.toUpperCase() }}<input v-model.number="modelPreset.position[axis]" type="number" step="0.05" @change="applyModelPreset()"></label>
        <label>{{ t('robotDebug.rotation') }}<input :value="rounded(modelPreset.rotationY * 180 / Math.PI)" type="number" step="1" @change="modelPreset.rotationY = Number($event.target.value) * Math.PI / 180; applyModelPreset()"></label>
        <label>{{ t('robotDebug.scale') }}<input v-model.number="modelPreset.scale" type="number" min="0.5" max="2" step="0.05" @change="applyModelPreset()"></label>
      </fieldset>
      <footer><button type="button" @click="copyDebugPreset">{{ t('robotDebug.copy') }}</button><button type="button" @click="factoryDebugPreset">{{ t('robotDebug.factory') }}</button><button type="button" @click="saveDebugPreset">{{ t('robotDebug.save') }}</button></footer>
    </details>
  </div>
</template>

<style scoped>
.robot-viewport{position:relative;width:100%;height:100%;min-height:0;touch-action:none}
.robot-viewport :deep(canvas){display:block;width:100%;height:100%;cursor:grab}
.robot-viewport :deep(canvas:active){cursor:grabbing}
.viewport-message{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;flex-direction:column;gap:12px;color:var(--text-secondary);font-size:12px;text-align:center}
.viewport-message button{border:1px solid color-mix(in srgb,var(--theme-primary) 35%,var(--info-divider));border-radius:8px;background:var(--info-background);color:var(--text-primary);font:inherit;cursor:pointer}
.viewport-message button{padding:7px 14px}
.viewport-controls{position:absolute;z-index:2;top:12px;right:12px;pointer-events:none}
.viewport-controls>*{pointer-events:auto}
.viewport-reset{display:grid;place-items:center;width:34px;height:34px;padding:0;color:var(--text-secondary);background:transparent;border:0;border-radius:50%;cursor:pointer;transition:color 180ms ease,transform 180ms ease}
.viewport-reset:hover{color:var(--theme-primary);transform:rotate(-30deg)}
.robot-debug-panel{position:absolute;z-index:3;top:12px;left:12px;width:248px;max-width:calc(100% - 24px);max-height:calc(100% - 80px);box-sizing:border-box;overflow:auto;padding:10px;color:var(--text-primary);background:var(--info-background);border:var(--info-border);border-radius:10px;box-shadow:var(--info-shadow);backdrop-filter:blur(14px)}
.robot-debug-panel summary{display:flex;align-items:center;justify-content:space-between;gap:8px;cursor:pointer;font-size:12px;font-weight:600}
.robot-debug-panel summary span{font-size:9px;font-weight:400;color:var(--theme-primary)}
.robot-debug-panel p{margin:8px 0;font-size:10px;line-height:1.5;color:var(--text-secondary)}
.robot-debug-panel fieldset{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px;margin:8px 0;padding:7px;border:1px solid var(--info-divider);border-radius:7px}
.robot-debug-panel legend{padding:0 3px;font-size:10px}
.robot-debug-panel label{display:grid;gap:3px;min-width:0;font-size:10px;color:var(--text-secondary)}
.robot-debug-panel input{box-sizing:border-box;width:100%;min-width:0;height:27px;padding:2px 5px;color:var(--text-primary);background:var(--info-background);border:1px solid var(--info-divider);border-radius:5px;font:inherit}
.robot-debug-panel footer{display:flex;flex-wrap:wrap;gap:5px;margin-top:8px}
.robot-debug-panel footer button{padding:5px 7px;color:var(--text-primary);background:var(--info-background);border:1px solid var(--info-divider);border-radius:6px;font-size:10px;cursor:pointer}
.robot-debug-panel footer button:last-child{color:var(--theme-primary);border-color:var(--theme-primary)}
</style>
