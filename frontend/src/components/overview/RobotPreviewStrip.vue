<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as THREE from 'three'
import { createGltfLoader, runtimeModelUrl } from '@/three/loaders/createGltfLoader.js'
import { SCENE_ASSETS } from '@/config/sceneAssets.js'

const props = defineProps({ theme: { type: String, default: 'light' }, count: { type: Number, default: 3 } })
const emit = defineEmits(['ready'])
const host = ref(null)
let renderer
let scene
let camera
let model
let resizeObserver
let loadGeneration = 0
let previewRadius = 1

const disposeObject = (root) => {
  if (!root) return
  const geometries = new Set()
  const materials = new Set()
  const textures = new Set()
  root.traverse((object) => {
    if (object.geometry) geometries.add(object.geometry)
    const list = Array.isArray(object.material) ? object.material : [object.material]
    list.filter(Boolean).forEach((material) => {
      materials.add(material)
      Object.values(material).forEach((value) => { if (value?.isTexture) textures.add(value) })
    })
  })
  geometries.forEach((item) => item.dispose())
  materials.forEach((item) => item.dispose())
  textures.forEach((item) => item.dispose())
}
const disposeModel = () => {
  if (!model) return
  disposeObject(model)
  scene?.remove(model)
  model = null
}

const applyTheme = () => {
  if (!scene) return
  const hemisphere = scene.getObjectByName('previewHemisphere')
  const key = scene.getObjectByName('previewKey')
  if (hemisphere) hemisphere.intensity = props.theme === 'dark' ? 1.45 : 2
  if (key) key.intensity = props.theme === 'dark' ? 2.1 : 2.8
  if (renderer) renderer.toneMappingExposure = props.theme === 'dark' ? 1.05 : 1.18
  renderPreview()
}

const resize = () => {
  const bounds = host.value?.getBoundingClientRect()
  if (!renderer || !bounds?.width || !bounds?.height) return
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
  renderer.setSize(bounds.width, bounds.height, false)
  renderPreview()
}

const renderPreview = () => {
  if (!renderer || !model || !host.value) return
  const width = host.value.clientWidth
  const height = host.value.clientHeight
  const cellWidth = width / Math.max(1, props.count)
  const halfHeight = previewRadius * 1.12 * Math.max(1, height / cellWidth)
  const halfWidth = halfHeight * (cellWidth / Math.max(1, height))
  camera.left = -halfWidth
  camera.right = halfWidth
  camera.top = halfHeight
  camera.bottom = -halfHeight
  camera.updateProjectionMatrix()
  renderer.setScissorTest(true)
  for (let index = 0; index < props.count; index += 1) {
    const left = Math.floor(index * cellWidth)
    const viewportWidth = Math.ceil(cellWidth)
    renderer.setViewport(left, 0, viewportWidth, height)
    renderer.setScissor(left, 0, viewportWidth, height)
    model.rotation.y = 0.22
    renderer.render(scene, camera)
  }
}

onMounted(() => {
  scene = new THREE.Scene()
  camera = new THREE.OrthographicCamera(-1.2, 1.2, 1.25, -1.25, 0.01, 20)
  camera.position.set(3, 2.2, 4.6)
  camera.lookAt(0, 0.72, 0)
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' })
  renderer.setClearColor(0x000000, 0)
  renderer.outputColorSpace = THREE.SRGBColorSpace
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.domElement.setAttribute('aria-label', '三台機器人模型預覽')
  host.value.appendChild(renderer.domElement)
  const hemisphere = new THREE.HemisphereLight(0xffffff, 0xb7aaa0, 2)
  hemisphere.name = 'previewHemisphere'
  const key = new THREE.DirectionalLight(0xfff4df, 2.8)
  key.name = 'previewKey'
  key.position.set(3, 5, 4)
  scene.add(hemisphere, key)
  applyTheme()
  resizeObserver = new ResizeObserver(resize)
  resizeObserver.observe(host.value)
  resize()
  const generation = ++loadGeneration
  createGltfLoader().load(runtimeModelUrl(SCENE_ASSETS.robot), (gltf) => {
    if (generation !== loadGeneration) { disposeObject(gltf.scene); return }
    model = gltf.scene
    const box = new THREE.Box3().setFromObject(model)
    const size = box.getSize(new THREE.Vector3())
    const center = box.getCenter(new THREE.Vector3())
    // Center the asset around its bounds; the same bounding sphere fits every preview.
    model.position.copy(center).negate()
    const pivot = new THREE.Group()
    pivot.add(model)
    model = pivot
    previewRadius = size.length() / 2
    camera.position.set(3, 2.2, 4.6).normalize().multiplyScalar(previewRadius * 4)
    camera.near = previewRadius * .01
    camera.far = previewRadius * 10
    camera.lookAt(0, 0, 0)
    scene.add(model)
    renderPreview()
    emit('ready')
  })
})

watch(() => props.theme, applyTheme)
onBeforeUnmount(() => {
  loadGeneration += 1
  resizeObserver?.disconnect()
  disposeModel()
  renderer?.dispose()
  renderer?.forceContextLoss()
  renderer?.domElement.remove()
  scene?.clear()
})
</script>

<template><div ref="host" class="robot-preview-strip" aria-hidden="true"></div></template>

<style scoped>
.robot-preview-strip{position:relative;width:64px;height:74px;overflow:visible;pointer-events:none}.robot-preview-strip :deep(canvas){display:block;width:100%;height:100%;border:0;outline:0;background:transparent}
</style>
