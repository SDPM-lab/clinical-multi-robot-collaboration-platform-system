<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { MapPin } from '@lucide/vue'
import * as THREE from 'three'
import { overviewPalette } from '@/styles/overviewTheme.js'
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js'
import { createGltfLoader, runtimeModelUrl } from '@/three/loaders/createGltfLoader.js'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import SharedLoading from '@/components/SharedLoading.vue'
import { webglProfile } from '@/three/webglProfile.js'
import { clinicOverviewModelUrl } from '@/data/clinicOverviewData.js'
import { applyOverviewArchitecturalMaterials, enhanceOverviewModelSaturation } from '@/three/overviewArchitecturalMaterials.js'
import { captureOverviewOriginalState, restoreOverviewOriginalState } from '@/three/overviewOriginalState.js'
import { addOverviewLighting, fitOverviewShadow, overviewLighting } from '@/three/clinicOverviewLighting.js'
import {
  buildOverviewFloorMapping,
  createOverviewFloorGroups,
  isOverviewFloorCameraNode,
  modelLoadPercentage,
} from '@/three/clinicFloorMapping.js'
import { cloneDefaultOverviewModelPreset } from '@/three/clinicOverviewPresets.js'
import { locale, t } from '@/i18n/index.js'

const props = defineProps({
  activeFloor: { type: [String, Number], default: 'all' },
  theme: { type: String, default: 'light' },
  cameraDebug: { type: Boolean, default: false },
  modelDebug: { type: Boolean, default: false },
  interactionTarget: { type: String, default: 'camera' },
  cameraPreset: { type: Object, default: null },
  modelPreset: { type: Object, default: cloneDefaultOverviewModelPreset },
})
const emit = defineEmits(['update:modelPreset', 'cameraChange', 'cameraPresetChange', 'floorAnchors', 'modelInteractionEnd'])

const host = ref(null)
const hospitalMarker = ref(null)
const loading = ref(true)
const loadError = ref(false)
const graphicsError = ref(false)
const renderProfile = webglProfile()
let disposed = false
const failGraphics = error => {
  if (disposed || graphicsError.value) return
  graphicsError.value = true
  loading.value = false
  cancelAnimationFrame(frameId)
  console.error('Overview WebGL rendering stopped:', error)
}
const onContextLost = event => { event.preventDefault(); failGraphics(new Error('WebGL context lost')) }
const retryScene = () => { if (graphicsError.value) window.location.reload(); else loadModel() }
const modelProgress = ref(0)
const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)')
const resources = { geometries: new Set(), materials: new Set(), textures: new Set() }
let floorGroups = createOverviewFloorGroups()
let floorStructureGroups = createOverviewFloorGroups()
let originalStates = new Map()
let appearanceStates = new Map()
let ceilingLightMeshes = []
let floorTintOverlays = []
let commonSceneObjects = []
let sharedBuildingObjects = []
const floorLocalCenters = new Map()
const floorLeaderPoints = new Map()
const floorCameraRules = Object.freeze({
  1: { padding: 1.48, direction: [0.18, 0.42, 1], targetLift: 0.02 },
  2: { padding: 1.48, direction: [0.18, 0.42, 1], targetLift: 0 },
  3: { padding: 1.5, direction: [0.18, 0.42, 1], targetLift: -0.01 },
})
const viewCameraPresets = { all: null, floor1: null, floor2: null, floor3: null }

let environmentTarget
let renderer
let scene
let camera
let controls
let layoutRoot
let modelRoot
let frameId
let resizeObserver
let loadGeneration = 0
let cameraTween
let dragState
let lastAnchorSignature = ''
let hospitalMarkerRoot
let hospitalMarkerAnchor
const hospitalMarkerWorld = new THREE.Vector3()
const hospitalMarkerProjected = new THREE.Vector3()

const easeOutQuint = (value) => 1 - ((1 - value) ** 5)
const roundedVector = (vector) => ({ x: Number(vector.x.toFixed(4)), y: Number(vector.y.toFixed(4)), z: Number(vector.z.toFixed(4)) })

const emitCameraState = () => emit('cameraChange', {
  position: camera ? roundedVector(camera.position) : { x: 0, y: 0, z: 0 },
  target: camera?.userData.target ? roundedVector(camera.userData.target) : { x: 0, y: 0, z: 0 },
})

const makeCameraPreset = () => ({ position: roundedVector(camera.position), target: roundedVector(controls?.target || camera.userData.target) })
const onCameraControlEnd = () => {
  camera.userData.target = controls.target.clone()
  const preset = makeCameraPreset()
  emit('cameraChange', preset)
  emit('cameraPresetChange', preset)
}

const rememberTexture = (value) => { if (value?.isTexture) resources.textures.add(value) }
const registerMaterial = (material) => {
  if (!material) return
  resources.materials.add(material)
  Object.values(material).forEach(rememberTexture)
}

const disposeDetachedScene = (root) => {
  const textures = new Set()
  root.traverse((object) => {
    object.geometry?.dispose?.()
    const materials = Array.isArray(object.material) ? object.material : [object.material]
    materials.forEach((material) => {
      if (!material) return
      Object.values(material).forEach((value) => { if (value?.isTexture) textures.add(value) })
      material.dispose()
    })
  })
  textures.forEach((texture) => texture.dispose())
}

const disposeModel = () => {
  if (layoutRoot) scene?.remove(layoutRoot)
  resources.geometries.forEach((geometry) => geometry.dispose())
  resources.materials.forEach((material) => material.dispose())
  resources.textures.forEach((texture) => texture.dispose())
  resources.geometries.clear()
  resources.materials.clear()
  resources.textures.clear()
  floorGroups = createOverviewFloorGroups()
  floorStructureGroups = createOverviewFloorGroups()
  originalStates.clear()
  appearanceStates.clear()
  ceilingLightMeshes = []
  floorTintOverlays = []
  commonSceneObjects = []
  sharedBuildingObjects = []
  floorLocalCenters.clear()
  floorLeaderPoints.clear()
  layoutRoot = null
  modelRoot = null
  hospitalMarkerRoot = null
  hospitalMarkerAnchor = null
}

const prepareHospitalRoute = (root) => {
  const routeRoot = root.getObjectByName('HOSPITAL_ROUTE_ROOT')
  routeRoot?.traverse((object) => {
    if (!object.isMesh || !object.material) return
    const array = Array.isArray(object.material)
    const materials = (array ? object.material : [object.material]).map((source) => {
      const material = source.clone()
      material.color?.set(overviewPalette.accent)
      if (material.emissive) {
        material.emissive.set(overviewPalette.accent)
        material.emissiveIntensity = 0.6
      }
      material.name = `${source.name || 'HospitalRoute'}_OverviewAccent`
      material.needsUpdate = true
      registerMaterial(material)
      return material
    })
    object.material = array ? materials : materials[0]
  })
}

const prepareHospitalMarker = (root) => {
  hospitalMarkerRoot = root.getObjectByName('HOSPITAL_MODEL_ROOT') || null
  hospitalMarkerAnchor = null
  if (!hospitalMarkerRoot) return
  root.updateMatrixWorld(true)
  const bounds = new THREE.Box3().setFromObject(hospitalMarkerRoot)
  if (bounds.isEmpty()) return
  const anchorWorld = bounds.getCenter(new THREE.Vector3())
  anchorWorld.y = bounds.max.y + 1.6
  hospitalMarkerAnchor = hospitalMarkerRoot.worldToLocal(anchorWorld)
}

const updateHospitalMarker = () => {
  const marker = hospitalMarker.value
  if (!marker || !hospitalMarkerRoot || !hospitalMarkerAnchor || !camera || !host.value) return
  hospitalMarkerRoot.localToWorld(hospitalMarkerWorld.copy(hospitalMarkerAnchor))
  hospitalMarkerProjected.copy(hospitalMarkerWorld).project(camera)
  const visible = hospitalMarkerProjected.z > -1 && hospitalMarkerProjected.z < 1
  marker.style.visibility = visible ? 'visible' : 'hidden'
  if (!visible) return
  const projectedX = (hospitalMarkerProjected.x * .5 + .5) * host.value.clientWidth
  const projectedY = (-hospitalMarkerProjected.y * .5 + .5) * host.value.clientHeight
  const screenX = THREE.MathUtils.clamp(projectedX, 72, host.value.clientWidth - 72)
  const screenY = THREE.MathUtils.clamp(projectedY, 132, host.value.clientHeight - 24)
  marker.dataset.edgeClamped = String(screenX !== projectedX || screenY !== projectedY)
  marker.style.transform = `translate(-50%, -100%) translate(${screenX}px, ${screenY}px)`
}

const reportDuplicateNodes = (root) => {
  if (!props.modelDebug) return
  const names = new Map()
  root.traverse((object) => {
    if (!object.name) return
    names.set(object.name, (names.get(object.name) || 0) + 1)
  })
  const duplicates = [...names.entries()].filter(([, count]) => count > 1).map(([name, count]) => ({ name, count }))
  console.table(duplicates)
  console.info(`[ClinicOverviewScene] duplicate node names: ${duplicates.length}`)
}

const reportModelHierarchy = (root) => {
  if (!props.modelDebug) return
  const hierarchy = []
  root.traverse((object) => {
    const materials = object.isMesh
      ? (Array.isArray(object.material) ? object.material : [object.material]).map((material) => material?.name).filter(Boolean).join(', ')
      : ''
    hierarchy.push({ name: object.name, type: object.type, parent: object.parent?.name || '', material: materials })
  })
  console.table(hierarchy)
}

const prepareModel = (root) => {
  originalStates = captureOverviewOriginalState(root, registerMaterial)
  applyOverviewArchitecturalMaterials(root, registerMaterial)
  enhanceOverviewModelSaturation(root)
  prepareHospitalRoute(root)
  prepareHospitalMarker(root)
  appearanceStates = captureOverviewOriginalState(root, registerMaterial)
  reportDuplicateNodes(root)
  reportModelHierarchy(root)
  root.traverse((object) => {
    if (!object.isMesh) return
    object.userData.overviewOriginalVisible = object.visible
    resources.geometries.add(object.geometry)
    const materials = Array.isArray(object.material) ? object.material : [object.material]
    materials.forEach((material) => {
      registerMaterial(material)

    })
    object.userData.overviewCastsShadow = true
    object.castShadow = true
    object.receiveShadow = true
  })
  root.updateMatrixWorld(true)
  const mapping = buildOverviewFloorMapping(root, THREE.Box3)
  floorGroups = mapping.groups
  floorStructureGroups = mapping.floorStructureGroups
  ceilingLightMeshes = mapping.ceilingLightMeshes
  commonSceneObjects = mapping.common
  sharedBuildingObjects = mapping.sharedBuilding
  sharedBuildingObjects.forEach((object) => { object.userData.overviewSharedBuilding = true })
  Object.entries(floorStructureGroups).forEach(([id, objects]) => {
    floorGroups[id].forEach((object) => { object.userData.overviewFloor = id })
    const bounds = objects.reduce((box, object) => box.expandByObject(object), new THREE.Box3())
    if (bounds.isEmpty()) return
    const center = bounds.getCenter(new THREE.Vector3())
    floorLeaderPoints.set(id, [bounds.min.x, bounds.max.x].flatMap((x) =>
      [bounds.min.z, bounds.max.z].map((z) => root.worldToLocal(new THREE.Vector3(x, center.y, z))),
    ))
    floorLocalCenters.set(id, root.worldToLocal(center.clone()))
  })
  if (props.modelDebug) console.table(Object.entries(floorStructureGroups).map(([floor, objects]) => ({
    floor,
    structures: objects.length,
    ceilingLights: ceilingLightMeshes.filter((object) => object.userData.overviewFloor === floor).length,
    names: objects.slice(0, 12).map(({ name }) => name).join(', '),
  })))
}

const createFloorTintOverlays = () => {
  const sources = new Set([
    ...Object.values(floorStructureGroups).flat(),
    ...sharedBuildingObjects,
  ])
  sources.forEach((source) => {
    if (!source.isMesh || !source.geometry) return
    const material = new THREE.MeshBasicMaterial({
      color: overviewPalette.accent,
      transparent: true,
      opacity: /glass/i.test(source.name) ? 0.08 : 0.13,
      depthWrite: false,
      depthTest: true,
      side: THREE.DoubleSide,
      polygonOffset: true,
      polygonOffsetFactor: -1,
      polygonOffsetUnits: -1,
    })
    material.name = 'OverviewSelectedFloorTint'
    registerMaterial(material)
    const overlay = new THREE.Mesh(source.geometry, material)
    overlay.name = `${source.name}_SelectedFloorTint`
    overlay.userData.overviewFloorTintOverlay = true
    overlay.userData.overviewTintFloor = source.userData.overviewFloor || 'shared'
    overlay.castShadow = false
    overlay.receiveShadow = false
    overlay.renderOrder = 20
    overlay.visible = false
    source.add(overlay)
    floorTintOverlays.push(overlay)
  })
}

const applyModelLayout = () => {
  if (!layoutRoot) return
  const preset = props.modelPreset
  layoutRoot.position.set(Number(preset.position.x) || 0, Number(preset.position.y) || 0, Number(preset.position.z) || 0)
  layoutRoot.scale.setScalar(THREE.MathUtils.clamp(Number(preset.scale) || 1, 0.1, 4))
  layoutRoot.rotation.set(Number(preset.rotation.x) || 0, Number(preset.rotation.y) || 0, Number(preset.rotation.z) || 0)
  layoutRoot.updateMatrixWorld(true)
  fitOverviewShadow(scene, layoutRoot)
}

const applyCameraPreset = (preset) => {
  if (!camera || !preset?.position || !preset?.target) return false
  const values = [
    Number(preset.position.x), Number(preset.position.y), Number(preset.position.z),
    Number(preset.target.x), Number(preset.target.y), Number(preset.target.z),
  ]
  if (!values.every(Number.isFinite)) return false
  cameraTween = null
  camera.position.set(values[0], values[1], values[2])
  const target = new THREE.Vector3(values[3], values[4], values[5])
  camera.userData.target = target
  controls?.target.copy(target)
  camera.lookAt(target)
  controls?.update()
  emitCameraState()
  return true
}

const applyFloorAppearance = () => {
  if (!modelRoot) return
  restoreOverviewOriginalState(appearanceStates)
  const selected = String(props.activeFloor)
  const selectedStructures = new Set(floorStructureGroups[selected] || [])
  const sharedStructures = new Set(sharedBuildingObjects)
  const hiddenLights = new Set(ceilingLightMeshes)
  renderer.clippingPlanes = []

  modelRoot.traverse((object) => {
    if (!object.isMesh) return
    if (object.userData.overviewFloorTintOverlay) {
      const overlayFloor = object.userData.overviewTintFloor
      object.visible = selected !== 'all' && overlayFloor === selected
      return
    }
    const isAll = selected === 'all'
    const isSelectedStructure = selectedStructures.has(object) || sharedStructures.has(object)
    const isLight = hiddenLights.has(object)
    object.visible = object.userData.overviewOriginalVisible && (isAll || !isLight)
    const materials = Array.isArray(object.material) ? object.material : [object.material]
    object.castShadow = object.userData.overviewCastsShadow && object.visible
    object.receiveShadow = object.visible
    materials.forEach((material, index) => {
      const original = appearanceStates.get(object)?.materials[index]
      if (!original) return
      if (original.color && material.color) material.color.copy(original.color)
      if (original.emissive && material.emissive) material.emissive.copy(original.emissive)
      if (Number.isFinite(original.emissiveIntensity)) material.emissiveIntensity = original.emissiveIntensity
      if (!isAll && !isSelectedStructure) {
        material.opacity = 0.22
        material.transparent = true
        material.depthWrite = false
      } else {
        material.opacity = original.opacity
        material.transparent = original.transparent
        material.depthWrite = original.depthWrite
      }
      material.needsUpdate = true
    })
  })
}

const restoreOverviewHome = () => {
  if (!camera) return
  // Cancel a floor tween even when the user returns home before it finishes.
  cameraTween = null
  const preset = props.cameraPreset
  viewCameraPresets.all = preset
  if (reducedMotion?.matches) { applyCameraPreset(preset); camera.userData.viewKey = 'all'; return }
  cameraTween = {
    startedAt: performance.now(), duration: 1100,
    fromPosition: camera.position.clone(), toPosition: new THREE.Vector3(preset.position.x, preset.position.y, preset.position.z),
    fromTarget: (controls?.target || camera.userData.target).clone(),
    toTarget: new THREE.Vector3(preset.target.x, preset.target.y, preset.target.z),
    viewKey: 'all',
  }
}

const frameSelection = (animate = true) => {
  if (!modelRoot || !camera || !host.value) return
  layoutRoot.updateMatrixWorld(true)
  const selected = String(props.activeFloor)
  const selectedObjects = (floorStructureGroups[selected] || []).filter((object) => (
    object.visible && isOverviewFloorCameraNode(object.name)
  ))
  const box = selectedObjects.length
    ? selectedObjects.reduce((bounds, object) => bounds.expandByObject(object), new THREE.Box3())
    : new THREE.Box3().setFromObject(modelRoot)
  if (!box || box.isEmpty()) return
  const floorMinY = box.min.y
  const floorMaxY = box.max.y
  sharedBuildingObjects.forEach((object) => {
    if (!object.visible) return
    const sharedBounds = new THREE.Box3().setFromObject(object)
    sharedBounds.min.y = Math.max(sharedBounds.min.y, floorMinY)
    sharedBounds.max.y = Math.min(sharedBounds.max.y, floorMaxY)
    if (!sharedBounds.isEmpty()) box.union(sharedBounds)
  })
  const size = box.getSize(new THREE.Vector3())
  const center = box.getCenter(new THREE.Vector3())
  const verticalFov = THREE.MathUtils.degToRad(camera.fov)
  const fitHeight = size.y / (2 * Math.tan(verticalFov / 2))
  const fitWidth = size.x / (2 * Math.tan(verticalFov / 2) * camera.aspect)
  const rule = floorCameraRules[selected]
  const direction = new THREE.Vector3(...rule.direction).normalize()
  const distance = Math.max(fitHeight, fitWidth) * rule.padding + size.z * 0.28
  center.y += size.y * rule.targetLift
  const targetPosition = center.clone().addScaledVector(direction, distance)
  viewCameraPresets[`floor${selected}`] = {
    position: roundedVector(targetPosition),
    target: roundedVector(center),
  }
  const duration = !animate || reducedMotion?.matches ? 0 : 1100
  camera.near = Math.max(0.05, distance / 140)
  camera.far = Math.max(120, distance + size.length() * 8)
  camera.updateProjectionMatrix()

  if (!duration) {
    camera.position.copy(targetPosition)
    camera.userData.target = center.clone()
    controls?.target.copy(center)
    camera.lookAt(center)
    controls?.update()
    cameraTween = null
    camera.userData.viewKey = `floor${selected}`
    emitCameraState()
    return
  }
  cameraTween = {
    startedAt: performance.now(), duration,
    fromPosition: camera.position.clone(), toPosition: targetPosition,
    fromTarget: camera.userData.target?.clone() || center.clone(), toTarget: center,
    viewKey: `floor${selected}`,
  }
}

const emitFloorAnchors = () => {
  if (!modelRoot || !camera || !host.value) return
  layoutRoot.updateMatrixWorld(true)
  const width = host.value.clientWidth
  const height = host.value.clientHeight
  const anchors = { viewportHeight: height }
  Object.entries(floorGroups).forEach(([floorId]) => {
    if (String(floorId) !== String(props.activeFloor)) return
    const localCenter = floorLocalCenters.get(floorId)
    if (!localCenter) return
    // Terminate at the visible left silhouette, not halfway across the building.
    const projected = (floorLeaderPoints.get(floorId) || [localCenter])
      .map((point) => modelRoot.localToWorld(point.clone()).project(camera))
      .reduce((left, point) => point.x < left.x ? point : left)
    anchors[floorId] = {
      x: Number((((projected.x + 1) / 2) * width).toFixed(1)),
      y: Number((((1 - projected.y) / 2) * height).toFixed(1)),
      visible: projected.z >= -1 && projected.z <= 1,
    }
  })
  const signature = JSON.stringify(anchors)
  if (signature !== lastAnchorSignature) {
    lastAnchorSignature = signature
    emit('floorAnchors', anchors)
  }
}

const applyTheme = () => {
  if (!renderer || !scene) return
  renderer.toneMappingExposure = overviewLighting.exposure
}

const animate = (time) => {
  if (disposed || graphicsError.value) return
  if (renderer?.getContext().isContextLost()) { failGraphics(new Error('WebGL context lost')); return }
  try {
  if (cameraTween) {
    const progress = Math.min((time - cameraTween.startedAt) / cameraTween.duration, 1)
    const eased = easeOutQuint(progress)
    camera.position.lerpVectors(cameraTween.fromPosition, cameraTween.toPosition, eased)
    const target = new THREE.Vector3().lerpVectors(cameraTween.fromTarget, cameraTween.toTarget, eased)
    camera.userData.target = target
    controls?.target.copy(target)
    camera.lookAt(target)
    if (progress === 1) {
      const completedViewKey = cameraTween.viewKey
      cameraTween = null
      controls?.target.copy(target)
      controls?.update()
      camera.userData.viewKey = completedViewKey || (String(props.activeFloor) === 'all' ? 'all' : `floor${props.activeFloor}`)
      emitCameraState()
    }
  }
  if (controls?.enabled) controls.update()
  emitFloorAnchors()
  updateHospitalMarker()
  renderer?.render(scene, camera)
  frameId = requestAnimationFrame(animate)
  } catch (error) { failGraphics(error) }
}

const loadModel = () => {
  const generation = ++loadGeneration
  loading.value = true
  loadError.value = false
  modelProgress.value = 0
  disposeModel()
  createGltfLoader().load(runtimeModelUrl(clinicOverviewModelUrl), (gltf) => {
    if (generation !== loadGeneration || graphicsError.value) {
      disposeDetachedScene(gltf.scene)
      return
    }
    modelRoot = gltf.scene
    layoutRoot = new THREE.Group()
    layoutRoot.name = 'ClinicOverviewLayout'
    layoutRoot.add(modelRoot)
    prepareModel(modelRoot)
    createFloorTintOverlays()
    scene.add(layoutRoot)
    applyModelLayout()
    applyFloorAppearance()
    if (String(props.activeFloor) === 'all') {
      viewCameraPresets.all = props.cameraPreset
      if (!applyCameraPreset(props.cameraPreset)) frameSelection(false)
      camera.userData.viewKey = 'all'
    } else frameSelection(false)
    modelProgress.value = 100
    requestAnimationFrame(() => { if (generation === loadGeneration) loading.value = false })
  }, (event) => {
    if (generation !== loadGeneration) return
    modelProgress.value = modelLoadPercentage(event)
  }, () => {
    if (generation !== loadGeneration) return
    loading.value = false
    loadError.value = true
  })
}

const resize = () => {
  if (!host.value || !renderer || !camera) return
  const { width, height } = host.value.getBoundingClientRect()
  if (!width || !height) return
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, renderProfile.maxPixelRatio))
  renderer.setSize(width, height, false)
  camera.aspect = width / height
  camera.fov = THREE.MathUtils.radToDeg(2 * Math.atan(Math.tan(THREE.MathUtils.degToRad(31 / 2)) * Math.max(1, (1366 / 768) / camera.aspect)))
  camera.updateProjectionMatrix()
  if (modelRoot) {
    if (String(props.activeFloor) === 'all') applyCameraPreset(props.cameraPreset)
    else frameSelection(false)
  }
}

const onPointerDown = (event) => {
  if (!props.modelDebug || props.interactionTarget !== 'model' || !layoutRoot) return
  const mode = event.button === 2 || event.altKey ? 'rotate' : event.shiftKey ? 'height' : 'translate'
  dragState = { pointerId: event.pointerId, x: event.clientX, y: event.clientY, mode }
  event.currentTarget.setPointerCapture(event.pointerId)
}
const onPointerMove = (event) => {
  if (!props.modelDebug || props.interactionTarget !== 'model' || !dragState || event.pointerId !== dragState.pointerId || !camera) return
  const dx = event.clientX - dragState.x
  const dy = event.clientY - dragState.y
  dragState.x = event.clientX
  dragState.y = event.clientY
  if (dragState.mode === 'rotate') {
    emit('update:modelPreset', {
      position: { ...props.modelPreset.position },
      rotation: {
        ...props.modelPreset.rotation,
        y: props.modelPreset.rotation.y + dx * 0.008,
      },
      scale: props.modelPreset.scale,
    })
    return
  }
  const distance = camera.position.distanceTo(camera.userData.target)
  const worldPerPixel = (2 * distance * Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2)) / host.value.clientHeight
  let movement
  if (dragState.mode === 'height') {
    movement = new THREE.Vector3(0, -dy * worldPerPixel, 0)
  } else {
    const right = new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld, 0).multiplyScalar(dx * worldPerPixel)
    const up = new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld, 1).multiplyScalar(-dy * worldPerPixel)
    movement = right.add(up)
  }
  emit('update:modelPreset', {
    ...props.modelPreset,
    position: {
      x: props.modelPreset.position.x + movement.x,
      y: props.modelPreset.position.y + movement.y,
      z: props.modelPreset.position.z + movement.z,
    },
    rotation: { ...props.modelPreset.rotation },
  })
}
const onPointerUp = (event) => {
  if (dragState?.pointerId === event.pointerId) {
    dragState = null
    emit('modelInteractionEnd')
  }
}
const onContextMenu = (event) => {
  if (props.modelDebug && props.interactionTarget === 'model') event.preventDefault()
}
const onWheel = (event) => {
  if (!props.modelDebug || props.interactionTarget !== 'model' || !layoutRoot) return
  event.preventDefault()
  emit('update:modelPreset', {
    position: { ...props.modelPreset.position },
    rotation: { ...props.modelPreset.rotation },
    scale: THREE.MathUtils.clamp(props.modelPreset.scale * Math.exp(-event.deltaY * 0.001), 0.35, 2.2),
  })
  emit('modelInteractionEnd')
}

watch(() => props.activeFloor, () => {
  applyFloorAppearance()
  if (String(props.activeFloor) === 'all') { applyModelLayout(); restoreOverviewHome(); return }
  frameSelection(true)
})
watch(() => props.theme, applyTheme)
watch(locale, () => renderer?.domElement?.setAttribute('aria-label', t('dashboard.sceneModel')))
watch(() => props.modelPreset, applyModelLayout, { deep: true })
watch(() => props.cameraPreset, (preset) => {
  if (preset && String(props.activeFloor) === 'all') applyCameraPreset(preset)
}, { deep: true })
watch(() => props.interactionTarget, () => {
  if (!controls) return
  controls.enabled = props.cameraDebug && props.interactionTarget === 'camera'
})

onMounted(() => {
  try {
  scene = new THREE.Scene()
  const sceneBackground = new THREE.Color(getComputedStyle(host.value).getPropertyValue('--bg-map').trim() || '#E8EDF2')
  scene.background = sceneBackground
  camera = new THREE.PerspectiveCamera(31, 1, 0.05, 200)
  camera.position.set(22, 18, 26)
  camera.userData.target = new THREE.Vector3()
  renderer = new THREE.WebGLRenderer({ antialias: renderProfile.antialias, alpha: true, powerPreference: renderProfile.powerPreference })
  renderer.setClearColor(sceneBackground, 0)
  renderer.setClearAlpha(0)
  renderer.outputColorSpace = THREE.SRGBColorSpace
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = THREE.PCFSoftShadowMap
  renderer.domElement.setAttribute('aria-label', t('dashboard.sceneModel'))
  renderer.domElement.addEventListener('webglcontextlost', onContextLost)
  renderer.domElement.addEventListener('pointerdown', onPointerDown)
  renderer.domElement.addEventListener('pointermove', onPointerMove)
  renderer.domElement.addEventListener('pointerup', onPointerUp)
  renderer.domElement.addEventListener('pointercancel', onPointerUp)
  renderer.domElement.addEventListener('contextmenu', onContextMenu)
  renderer.domElement.addEventListener('wheel', onWheel, { passive: false })
  host.value.prepend(renderer.domElement)
  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.075
  controls.screenSpacePanning = true
  controls.minDistance = 6
  controls.maxDistance = 100
  controls.enabled = props.cameraDebug && props.interactionTarget === 'camera'
  controls.addEventListener('end', onCameraControlEnd)

  const pmrem = new THREE.PMREMGenerator(renderer)
  const room = new RoomEnvironment()
  environmentTarget = pmrem.fromScene(room, 0.04)
  scene.environment = environmentTarget.texture
  scene.environmentIntensity = 0.28
  room.dispose()
  pmrem.dispose()
  addOverviewLighting(scene)
  applyTheme()
  resizeObserver = new ResizeObserver(resize)
  resizeObserver.observe(host.value)
  resize()
  loadModel()
  frameId = requestAnimationFrame(animate)
  } catch (error) { failGraphics(error) }
})

onBeforeUnmount(() => {
  disposed = true
  loadGeneration += 1
  cancelAnimationFrame(frameId)
  resizeObserver?.disconnect()
  if (renderer?.domElement) {
    renderer.domElement.removeEventListener('webglcontextlost', onContextLost)
    renderer.domElement.removeEventListener('pointerdown', onPointerDown)
    renderer.domElement.removeEventListener('pointermove', onPointerMove)
    renderer.domElement.removeEventListener('pointerup', onPointerUp)
    renderer.domElement.removeEventListener('pointercancel', onPointerUp)
    renderer.domElement.removeEventListener('contextmenu', onContextMenu)
    renderer.domElement.removeEventListener('wheel', onWheel)
  }
  controls?.removeEventListener('end', onCameraControlEnd)
  controls?.dispose()
  disposeModel()
  scene?.traverse((object) => { if (object.isLight) object.dispose?.() })
  environmentTarget?.dispose()
  renderer?.dispose()
  renderer?.forceContextLoss()
  renderer?.domElement.remove()
  scene?.clear()
})

defineExpose({
  resetCamera: restoreOverviewHome,
  resetModel: () => { restoreOverviewOriginalState(appearanceStates); applyModelLayout(); restoreOverviewHome() },
  getViewState: () => {
    let alteredMaterials = 0
    modelRoot?.traverse((object) => {
      if (!object.isMesh) return
      for (const material of Array.isArray(object.material) ? object.material : [object.material]) {
        const mats = Array.isArray(object.material) ? object.material : [object.material]
        const original = appearanceStates.get(object)?.materials[mats.indexOf(material)]
        if (original && (material.opacity !== original.opacity || material.transparent !== original.transparent || material.depthWrite !== original.depthWrite || (original.color && !material.color.equals(original.color)) || (original.emissive && !material.emissive.equals(original.emissive)))) alteredMaterials += 1
      }
    })
    return {
      ...makeCameraPreset(), tweening: Boolean(cameraTween), alteredMaterials,
      floors: Object.entries(floorGroups).map(([id, objects]) => ({ id, count: objects.length, visible: objects.filter((object) => object.visible).length })),
      floorStructures: Object.fromEntries(Object.entries(floorStructureGroups).map(([id, objects]) => [id, objects.map((object) => object.name)])),
      ceilingLightMeshes: ceilingLightMeshes.map((object) => object.name),
      commonObjects: commonSceneObjects.length,
      sharedBuildingObjects: sharedBuildingObjects.length,
      viewKey: camera?.userData.viewKey,
      viewCameraPresets: JSON.parse(JSON.stringify(viewCameraPresets)),
      progress: modelProgress.value,
    }
  },
})
</script>

<template>
  <section ref="host" class="clinic-overview-scene" :class="{ 'is-debug': modelDebug || cameraDebug, 'is-model-debug': modelDebug && interactionTarget === 'model' }">
    <div ref="hospitalMarker" class="hospital-location-marker" :aria-label="t('common.brandLocation')">
      <span class="hospital-location-marker__pin"><MapPin :size="24" :stroke-width="2" /></span>
      <strong>MediSync</strong>
    </div>
    <SharedLoading :loading="loading && !graphicsError" :detail="`${modelProgress}%`" :error="graphicsError ? '3D 畫面暫時無法繪製，請重新載入頁面。若仍未恢復，請關閉其他 3D 分頁並重新啟動瀏覽器。' : loadError ? '請確認模型檔案後重新載入。' : ''" :error-title="graphicsError ? '3D 顯示中斷' : '模型載入失敗'">
      <template #error-action><button class="clinic-model-retry" type="button" @click="retryScene">重新載入</button></template>
    </SharedLoading>
  </section>
</template>

<style scoped>
.clinic-overview-scene{position:relative;width:100%;height:100%;min-height:360px;overflow:hidden;background:var(--bg-map,#E8EDF2);isolation:isolate}:deep(canvas){position:absolute;z-index:1;inset:0;display:block;width:100%;height:100%;border:0;outline:0;background:transparent;pointer-events:none}.clinic-overview-scene.is-debug :deep(canvas){cursor:grab;pointer-events:auto}.clinic-overview-scene.is-model-debug :deep(canvas:active){cursor:grabbing}.clinic-model-retry{padding:7px 11px;color:#1e1f1e;background:var(--overview-accent);border:0;border-radius:6px;cursor:pointer}
:deep(canvas){mask-image:radial-gradient(ellipse 95% 100% at 52% 48%,#000 65%,rgba(0,0,0,.94) 82%,transparent 100%);-webkit-mask-image:radial-gradient(ellipse 95% 100% at 52% 48%,#000 65%,rgba(0,0,0,.94) 82%,transparent 100%)}
.hospital-location-marker{position:absolute;z-index:3;top:0;left:0;display:grid;justify-items:center;gap:3px;visibility:hidden;pointer-events:none;will-change:transform}.hospital-location-marker__pin{display:grid;width:34px;height:34px;place-items:center;color:#fff;background:var(--color-primary);border:1px solid var(--marker-border);border-radius:50% 50% 50% 12px;box-shadow:var(--marker-shadow);transform:rotate(-45deg)}.hospital-location-marker__pin :deep(svg){transform:rotate(45deg)}.hospital-location-marker strong{padding:5px 9px;color:var(--color-text);font-size:11px;font-weight:600;line-height:1;background:var(--marker-background);border:1px solid var(--marker-border);border-radius:var(--radius-control);box-shadow:var(--marker-shadow);backdrop-filter:var(--control-backdrop);white-space:nowrap}
</style>
