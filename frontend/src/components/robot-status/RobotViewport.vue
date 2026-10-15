<script setup>
import { onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { RotateCcw } from '@lucide/vue'
import { AgibotArmAssembly } from '@/three/robot/AgibotArmAssembly.js'
import { defaultRobotModelPreset, readRobotCameraPreset, readRobotModelPreset, storeRobotCameraPreset, storeRobotModelPreset, validRobotCameraPreset, validRobotModelPreset } from '@/config/robotViewportPreset.js'
import { t } from '@/i18n/index.js'

const modelUrl = `${import.meta.env.BASE_URL}models/AGIBOT_A2D.glb`
const params = new URLSearchParams(window.location.search)
const robotDebugEnabled = params.get('robotDebug') === '1'
const cameraDebugEnabled = robotDebugEnabled && params.get('cameraDebug') === '1'
const modelDebugEnabled = robotDebugEnabled && params.get('modelDebug') === '1'
const debugEnabled = cameraDebugEnabled || modelDebugEnabled
let assetPromise
function loadAsset() {
  if (!assetPromise) assetPromise = new GLTFLoader().loadAsync(modelUrl).catch(error => {
    assetPromise = null
    throw error
  })
  return assetPromise
}

const props = defineProps({ robotId: String })
const emit = defineEmits(['ready'])
const host = ref(null)
const loading = ref(true)
const error = ref('')
const disassembly = ref(0)
const debugStatus = ref('')
const cameraPreset = reactive({ position: { x: 0, y: 0, z: 0 }, target: { x: 0, y: 0, z: 0 }, fov: 35, aspect: 1 })
const modelPreset = reactive(readRobotModelPreset() || defaultRobotModelPreset())
let renderer, scene, camera, controls, observer, assembly, model, frame
let disposed = false
let currentAmount = 0
let lastFrame = 0
let viewportWidth = 0
let viewportHeight = 0
const frontDirection = new THREE.Vector3(1, .13, .28).normalize()
const rounded = value => Math.round(value * 1000) / 1000

function captureCamera() {
  if (!camera || !controls || !debugEnabled) return
  for (const axis of ['x', 'y', 'z']) {
    cameraPreset.position[axis] = rounded(camera.position[axis])
    cameraPreset.target[axis] = rounded(controls.target[axis])
  }
  cameraPreset.fov = rounded(camera.fov)
  cameraPreset.aspect = camera.aspect
}

function applyCameraPreset(preset = cameraPreset) {
  if (!camera || !controls || !validRobotCameraPreset(preset)) { debugStatus.value = t('robotDebug.invalid'); return }
  camera.position.set(Number(preset.position.x), Number(preset.position.y), Number(preset.position.z))
  controls.target.set(Number(preset.target.x), Number(preset.target.y), Number(preset.target.z))
  camera.fov = Number(preset.fov)
  camera.updateProjectionMatrix()
  if (assembly && preset.aspect) {
    const direction = camera.position.clone().sub(controls.target).normalize()
    const bounds = assembly.boundsAt(currentAmount)
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
    const amount = currentAmount
    assembly.set(0)
    assembly.assembledBounds.setFromObject(model)
    assembly.set(1)
    assembly.explodedBounds.setFromObject(model)
    assembly.set(amount)
    resize()
  }
  debugStatus.value = ''
}

function saveDebugPreset() {
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

function fitFactoryView() {
  if (!assembly || !camera || !controls) return
  camera.fov = 35
  camera.updateProjectionMatrix()
  const bounds = assembly.boundsAt(disassembly.value / 100)
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
  if (saved) applyCameraPreset(saved)
  captureCamera()
}

function resize() {
  if (!host.value || !renderer || !camera) return
  const { width, height } = host.value.getBoundingClientRect()
  if (width < 1 || height < 1) return
  const sizeChanged = width !== viewportWidth || height !== viewportHeight
  const bounds = assembly?.boundsAt(currentAmount)
  const direction = controls && camera.position.clone().sub(controls.target).normalize()
  const previousFit = bounds && direction && viewportWidth && viewportHeight && sizeChanged
    ? fitDistance(bounds, direction)
    : 0
  renderer.setSize(width, height, false)
  camera.aspect = width / height
  camera.updateProjectionMatrix()
  viewportWidth = width
  viewportHeight = height
  if (!assembly || !controls) return
  const needed = fitDistance(bounds, direction)
  const distance = camera.position.distanceTo(controls.target)
  // Preserve the user's zoom across fullscreen and other container resizes.
  const nextDistance = previousFit
    ? distance * needed / previousFit
    : Math.max(distance, needed)
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
  const target = disassembly.value / 100
  const transitioning = currentAmount !== target
  if (transitioning) {
    currentAmount = Math.abs(currentAmount - target) < .0005
      ? target
      : THREE.MathUtils.lerp(currentAmount, target, 1 - Math.exp(-9 * delta))
    assembly.set(currentAmount)
  }
  if (transitioning) {
    const direction = camera.position.clone().sub(controls.target).normalize()
    const needed = fitDistance(assembly.boundsAt(Math.max(currentAmount, target)), direction)
    const distance = camera.position.distanceTo(controls.target)
    if (distance < needed) camera.position.copy(controls.target).addScaledVector(direction, needed)
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
  loading.value = true
  error.value = ''
  try {
    initializeRenderer()
    const asset = await loadAsset()
    if (disposed) return
    if (!asset.scene.getObjectByName('AGIBOT_A2D')) throw new Error('AGIBOT_A2D root node missing')
    model = asset.scene.clone(true)
    scene.add(model)
    applyModelPreset()
    assembly = new AgibotArmAssembly(model)
    currentAmount = 0
    disassembly.value = 0
    resize()
    resetView()
    loading.value = false
    emit('ready')
    if (!frame) frame = requestAnimationFrame(animate)
  } catch (reason) {
    if (disposed) return
    loading.value = false
    error.value = 'AGIBOT A2D 3D 模型載入失敗。'
    console.error(reason)
  }
}

function toggleDisassembly() { disassembly.value = disassembly.value > 0 ? 0 : 100 }
watch(() => props.robotId, () => {
  disassembly.value = 0
  currentAmount = 0
  assembly?.set(0)
  resetView()
})
onMounted(start)
onBeforeUnmount(() => {
  disposed = true
  cancelAnimationFrame(frame)
  observer?.disconnect()
  if (debugEnabled) controls?.removeEventListener('end', captureCamera)
  controls?.dispose()
  if (model) scene?.remove(model)
  renderer?.forceContextLoss()
  renderer?.dispose()
  renderer?.domElement.remove()
})
defineExpose({ resetView })
</script>

<template>
  <div ref="host" class="robot-viewport" aria-label="AGIBOT A2D 互動式 3D 模型">
    <div v-if="loading" class="viewport-message" role="status">Loading...</div>
    <div v-else-if="error" class="viewport-message" role="alert">{{ error }}<button type="button" @click="start">重試</button></div>
    <div v-else class="viewport-controls">
      <button type="button" class="viewport-reset" @click="resetView"><RotateCcw :size="14" aria-hidden="true"/>重設視角</button>
      <div class="viewport-disassembly">
        <button type="button" @click="toggleDisassembly">{{ disassembly ? '恢復組裝' : '手臂拆解' }}</button>
        <label>拆解程度 <input v-model.number="disassembly" type="range" min="0" max="100" step="1" aria-label="手臂拆解程度"><output>{{ disassembly }}%</output></label>
      </div>
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
.viewport-message button,.viewport-controls button{border:1px solid color-mix(in srgb,var(--theme-primary) 35%,var(--info-divider));border-radius:8px;background:var(--info-background);color:var(--text-primary);font:inherit;cursor:pointer}
.viewport-message button{padding:7px 14px}
.viewport-controls{position:absolute;z-index:2;right:12px;bottom:12px;left:12px;display:flex;align-items:flex-end;justify-content:space-between;gap:10px;pointer-events:none}
.viewport-controls>*{pointer-events:auto}
.viewport-reset{display:flex;align-items:center;gap:6px;padding:8px 10px;font-size:11px!important}
.viewport-disassembly{display:flex;flex-direction:column;align-items:flex-end;gap:6px;padding:8px 10px;border:1px solid var(--info-divider);border-radius:10px;background:var(--info-background);box-shadow:var(--info-shadow)}
.viewport-disassembly button{padding:5px 9px;color:var(--theme-primary);font-size:11px}
.viewport-disassembly label{display:flex;align-items:center;gap:8px;white-space:nowrap;color:var(--text-secondary);font-size:10px}
.viewport-disassembly input{width:110px;accent-color:var(--theme-primary)}
.viewport-disassembly output{min-width:32px;text-align:right;font-variant-numeric:tabular-nums}
@media(max-width:480px){.viewport-controls{flex-wrap:wrap}.viewport-disassembly input{width:85px}}
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
