<script setup>
import { visualTokens, colorHex } from '@/config/visualTokens.js'
import SharedLoading from '@/components/SharedLoading.vue'
import { dispatchWaypointLabels } from '@/config/dispatchDestinations.js'
import { locale, t, translateTask, translateLocation } from '@/i18n/index.js'
import { computed, nextTick, onActivated, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as THREE from 'three'
import { Bot, Camera, Eye, Layers3, LayoutDashboard, LocateFixed, Orbit, RotateCcw, Route, Plus, Minus, X } from '@lucide/vue'
import { createGltfLoader, runtimeModelUrl } from '@/three/loaders/createGltfLoader.js'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { getEmbeddedAssetLayer, SCENE_ASSETS } from '@/config/sceneAssets.js'
import { NAVIGATION_ASSETS } from '@/config/sceneAssets.js'
import {
  actorVisibility,
  baymaxConfig,
} from '@/config/baymaxNurseConfig.js'
import { graphActorConfig } from '@/config/graphActorConfig.js'
import { BaymaxNurseController } from '@/three/actors/BaymaxNurseController.js'
import {
  buildGraphActorPlan,
  GraphActorCoordinator,
} from '@/three/actors/GraphActorCoordinator.js'
import {
  applyOverviewMaterials,
  disposeOverviewMaterials,
  updateOverviewMaterialTheme,
} from '@/three/materials/overviewMaterials.js'
import { getSceneLighting } from '@/three/lighting/sceneLighting.js'
import { getSceneTheme } from '@/three/sceneTheme.js'
import { collectOverviewMeshMaterialRows } from '@/three/overviewMaterialRules.js'
import {
  buildActiveRoutes,
  buildLocationDetails,
  demoRobotWaypoints,
  priorityOrder,
  robotRouteColors,
  sortTasksByPriority,
} from '@/data/demoActiveRoutes.js'
import { RmfNavigationLayer } from '@/three/navigation/RmfNavigationLayer.js'
import { LocationMarkerLayer } from '@/three/navigation/LocationMarkerLayer.js'
import { RoomLabelLayer } from '@/three/navigation/RoomLabelLayer.js'
import { RmfDoorController } from '@/three/navigation/RmfDoorController.js'
import { MapAlignmentDebug } from '@/three/navigation/MapAlignmentDebug.js'
import { getRobotCameraPose } from '@/three/navigation/realtimeRobotCamera.js'
import { demoFleetStore } from '@/stores/demoFleetStore.js'
import { taskApi } from '@/services/taskApi.js'
import { adaptLiveMapSnapshot, orderLiveMapRobots, buildLiveMapRoutes, buildLiveMapLocationDetails, withPreviewPositions, placeSimulatedRobotsAtRouteStart } from '@/data/liveMapSnapshot.js'
import { getRobotVisualTheme } from '@/config/robotVisualThemes.js'
import { robotDisplayCode } from '@/config/robotDisplayCode.js'
import { rmfToThree } from '@/config/rmfMapTransform.js'
import {
  DEFAULT_OVERVIEW_CAMERA_PRESET,
  isOverviewCameraPreset,
  readStoredOverviewCameraPreset,
  storeOverviewCameraPreset,
} from '@/three/overviewCameraPreset.js'
import {
  DEFAULT_REALTIME_MAP_CAMERA_PRESET,
  isRealtimeMapCameraPreset,
  readStoredRealtimeMapCameraPreset,
  storeRealtimeMapCameraPreset,
} from '@/three/realtimeMapCameraPreset.js'

const props = defineProps({
  modelUrl: {
    type: String,
    default: SCENE_ASSETS.environment,
  },
  mode: {
    type: String,
    default: 'overview',
    validator: (value) => ['overview', 'original'].includes(value),
  },
  theme: {
    type: String,
    default: 'light',
    validator: (value) => ['light', 'dark'].includes(value),
  },
})

const container = ref(null)
const loading = ref(true)
const progress = ref(0)
const errorMessage = ref('')
const actorErrorMessage = ref('')
const navigationData = ref(null)
const showLocations = ref(true)
const showNavigation = ref(true)
const showActiveRoute = ref(true)
const showActors = ref(true)
const showRobots = ref(true)
const showTaskLabels = ref(true)
const showRoomLabels = ref(true)
const showRouteArrows = ref(true)
const alignmentVertexId = ref('v0')
const activeMapTool = ref(null)
const activeFloor = ref(1)
const floorPicker = ref(null)
const floorMenuOpen = ref(false)
const floorOptions = [1, 2, 3]
const openFloorMenu = async () => {
  floorMenuOpen.value = true
  await nextTick()
  floorPicker.value?.querySelector('[aria-checked="true"]')?.focus()
}
const closeFloorMenu = () => {
  floorMenuOpen.value = false
  floorPicker.value?.querySelector('.floor-trigger')?.focus()
}
const handleFloorMenuKeydown = event => {
  if (event.key === 'Escape') { event.preventDefault(); closeFloorMenu(); return }
  const options = [...(floorPicker.value?.querySelectorAll('.floor-option') || [])]
  const current = options.indexOf(document.activeElement)
  const next = event.key === 'ArrowDown' ? (current + 1) % options.length
    : event.key === 'ArrowUp' ? (current + options.length - 1) % options.length
      : event.key === 'Home' ? 0 : event.key === 'End' ? options.length - 1 : -1
  if (next >= 0) { event.preventDefault(); options[next]?.focus() }
}
const onFloorPickerOutside = event => {
  if (!floorPicker.value?.contains(event.target)) floorMenuOpen.value = false
}
const liveSnapshot = ref({robots:[],tasks:[]})
const liveMapLoading = ref(false)
const liveMapError = ref('')
let livePollTimer
let liveRequestActive = false
let liveNavigationSignature = ''
const previewPlacements = new Map()
const arrivalRequests = new Set()
const arrivalRetryAt = new Map()
const refreshLiveMap = async () => {
  if (props.mode !== 'original' || disposed || liveRequestActive) return
  liveRequestActive = true
  liveMapLoading.value = true
  try {
    const [robots,tasks] = await Promise.all([taskApi.getRobotSnapshot(),taskApi.getTaskRecords()])
    if (!disposed) { liveSnapshot.value = adaptLiveMapSnapshot(robots,tasks); liveMapError.value = '' }
  } catch (error) { if (!disposed) liveMapError.value = error.message || t('dispatch.apiLoadError') }
  finally { liveRequestActive = false; liveMapLoading.value = false }
}
const completeArrivedSimulations = () => {
  if (props.mode !== 'original' || !navigationLayer || !navigationData.value) return
  const destinations = new Map(navigationData.value.namedWaypoints.map(point => [point.name, point]))
  for (const task of mapStore.tasks.value) {
    if (!task.isSimulated || task.status !== 'executing' || !task.robotId || arrivalRequests.has(task.id) ||
        (arrivalRetryAt.get(task.id) || 0) > Date.now()) continue
    const destination = destinations.get(task.backendDestination || task.destinationId)
    const route = buildLiveMapRoutes(navigationData.value, [task])[0]
    if (!destination || route?.vertexIds.at(-1) !== destination.id) continue
    const state = navigationLayer.getRobotRouteState(task.robotId)
    const position = navigationLayer.getRobotPosition(task.robotId)
    const target = rmfToThree(destination)
    if (!state || state.progress < 0.9999 || !position || Math.hypot(position.x - target.x, position.z - target.z) > 0.2) continue
    arrivalRequests.add(task.id)
    taskApi.completeSimulatedArrival(task.id, task.robotId, task.source, task.backendDestination)
      .then(() => {
        previewPlacements.set(task.robotId, { x: destination.x, y: destination.y, yaw: 0 })
        return refreshLiveMap()
      })
      .catch(() => { arrivalRetryAt.set(task.id, Date.now() + 5000) })
      .finally(() => arrivalRequests.delete(task.id))
  }
}
const mapStore = { robots:computed(()=>props.mode==='original' ? liveSnapshot.value.robots : demoFleetStore.robots.value), tasks:computed(()=>props.mode==='original' ? liveSnapshot.value.tasks : demoFleetStore.tasks.value) }
const floorRobots = computed(()=>mapStore.robots.value.filter(robot=>robot.floorId===`floor${activeFloor.value}`))
const unlocatedRobots = computed(()=>mapStore.robots.value.filter(robot=>!robot.floorId))
const showRunningTasks = ref(true)
const floorTasks = computed(() => activeTasks.value.filter(task =>
  mapStore.robots.value.find(robot => robot.id === task.robotId)?.floorId === `floor${activeFloor.value}`,
))
const zoomRealtimeMap = factor => {
  if (!camera || !controls) return
  const offset = camera.position.clone().sub(controls.target)
  const distance = Math.max(controls.minDistance || 1, Math.min(controls.maxDistance || Infinity, offset.length() * factor))
  camera.position.copy(controls.target).add(offset.setLength(distance))
  controls.update()
}
const selectFloor = floor => {
  activeFloor.value = floor
  activeMapTool.value = null
  resetRealtimeFocus()
  closeFloorMenu()
}
const selectedRobotId = ref(null)
const robotDrawerFilter = ref('all')
const followRobotId = ref(null)
const realtimeSelectedTaskId = ref(null)
const cameraMode = ref('global')
const cameraMenuOpen = ref(false)
const priorityFilters = ref({ emergency: true, high: true, normal: true, low: true })
const isolatePriorities = ref(false)
const followWindow = ref({ visible: false, x: 0, y: 0 })
const activeTasks = computed(() => sortTasksByPriority(
  mapStore.tasks.value.filter((task) => task.status === 'executing'),
))
const activeRobotId = computed(() => followRobotId.value || selectedRobotId.value)
const selectedRobot = computed(() => mapStore.robots.value.find((robot) => robot.id === activeRobotId.value))
const selectedRobotTasks = computed(() => sortTasksByPriority(
  mapStore.tasks.value.filter((task) => task.robotId === activeRobotId.value),
))
const selectedActiveTask = computed(() => selectedRobotTasks.value.find((task) => task.status === 'executing'))
const selectedQueuedTasks = computed(() => selectedRobotTasks.value.filter((task) => ['scheduled', 'pending', 'assigned'].includes(task.status)))
const robotDrawerCounts = computed(() => ({
  all: floorRobots.value.length,
  busy: floorRobots.value.filter((robot) => robot.state === 'busy').length,
  idle: floorRobots.value.filter((robot) => robot.state === 'idle').length,
}))
const filteredDrawerRobots = computed(() => robotDrawerFilter.value === 'all'
  ? orderLiveMapRobots(floorRobots.value)
  : floorRobots.value.filter((robot) => robot.state === robotDrawerFilter.value))
const selectedRobotTheme = computed(() => getRobotVisualTheme(activeRobotId.value))
const robotInfoCardStyle = computed(() => ({
  '--robot-card-color': selectedRobotTheme.value.soft,
  '--robot-card-border': selectedRobotTheme.value.main,
  '--robot-card-glow': selectedRobotTheme.value.soft,
  '--robot-color': selectedRobotTheme.value.main,
  '--robot-soft': selectedRobotTheme.value.soft,
}))
const selectedPriorities = computed(() => Object.entries(priorityFilters.value).filter(([, enabled]) => enabled).map(([priority]) => priority))
const normalizedPriority = (priority) => priorityOrder[priority] === undefined ? 'normal' : priority
const mapTools = Object.freeze([
  { id: 'overview', label: '總覽', icon: LayoutDashboard },
  { id: 'robots', label: '機器人', icon: Bot },
  { id: 'tasks', label: '執行中任務', icon: Route },
  { id: 'layers', label: '地圖圖層', icon: Layers3 },
])

let scene
let camera
let renderer
let controls
let resizeObserver
let animationFrameId
let environmentGroup
let actorGroup
let robotGroup
let characterGroup
let overlayGroup
let hemisphereLight
let ambientLight
let directionalLight
let fillLight
let environmentBounds
let environmentCenter
let backgroundTransition
let baymaxControllers = []
let graphActorCoordinator
let navigationLayer
let locationMarkerLayer
let roomLabelLayer
let doorController
let mapAlignmentDebug
let cameraFocusTransition
let pointerStart
let pointerDragged = false
const robotRaycaster = new THREE.Raycaster()
const pointerNdc = new THREE.Vector2()
let disposed = false
const sceneClock = new THREE.Clock(false)

let lighting = getSceneLighting(props.mode, props.theme)
const isOverview = props.mode === 'overview'
const searchParams = new URLSearchParams(window.location.search)
const cameraDebugEnabled = isOverview
  ? searchParams.get('cameraDebug') === '1'
  : false
const mapCameraDebugEnabled = !isOverview
  && searchParams.get('mapCameraDebug') === '1'
const mapAlignmentDebugEnabled = import.meta.env.DEV
  && !isOverview
  && searchParams.get('mapAlignmentDebug') === '1'

const disposeMaterial = (material, disposedTextures) => {
  if (!material) return

  for (const value of Object.values(material)) {
    if (value?.isTexture && !disposedTextures.has(value)) {
      disposedTextures.add(value)
      value.dispose()
    }
  }

  material.dispose()
}

const disposeObject = (object) => {
  const disposedTextures = new Set()

  object?.traverse((child) => {
    child.geometry?.dispose()

    if (Array.isArray(child.material)) {
      child.material.forEach((material) => disposeMaterial(material, disposedTextures))
    } else {
      disposeMaterial(child.material, disposedTextures)
    }
  })
}

const updateRendererSize = () => {
  if (!container.value || !camera || !renderer) return

  const width = Math.max(container.value.clientWidth, 1)
  const height = Math.max(container.value.clientHeight, 1)

  const aspect = width / height

  camera.aspect = aspect
  if (!isOverview) camera.fov = THREE.MathUtils.radToDeg(2 * Math.atan(Math.tan(THREE.MathUtils.degToRad(42 / 2)) * Math.max(1, (1366 / 768) / aspect)))
  camera.updateProjectionMatrix()

  renderer.setSize(width, height, false)
}

const prepareModelBounds = (model) => {
  if (!environmentBounds) {
    const initialBounds = new THREE.Box3().setFromObject(model)
    if (initialBounds.isEmpty()) throw new Error('模型內沒有可顯示的幾何物件。')

    const initialCenter = initialBounds.getCenter(new THREE.Vector3())
    model.position.x -= initialCenter.x
    model.position.y -= initialBounds.min.y
    model.position.z -= initialCenter.z
    model.updateMatrixWorld(true)
    environmentBounds = new THREE.Box3().setFromObject(model)
    environmentCenter = environmentBounds.getCenter(new THREE.Vector3())
  }
}

const updateSceneLighting = () => {
  const size = environmentBounds.getSize(new THREE.Vector3())
  const maxDimension = Math.max(size.x, size.y, size.z)
  const shadowSpan = Math.max(size.x, size.z) * 0.8

  directionalLight.position.set(
    maxDimension * lighting.key.position[0],
    maxDimension * lighting.key.position[1],
    maxDimension * lighting.key.position[2],
  )
  directionalLight.target.position.copy(environmentCenter)
  directionalLight.shadow.camera.left = -shadowSpan
  directionalLight.shadow.camera.right = shadowSpan
  directionalLight.shadow.camera.top = shadowSpan
  directionalLight.shadow.camera.bottom = -shadowSpan
  directionalLight.shadow.camera.near = Math.max(maxDimension * 0.01, 0.01)
  directionalLight.shadow.camera.far = maxDimension * 5
  directionalLight.shadow.intensity = lighting.key.shadowIntensity
  directionalLight.shadow.bias = lighting.key.shadowBias
  directionalLight.shadow.normalBias = lighting.key.shadowNormalBias
  directionalLight.shadow.camera.updateProjectionMatrix()
  scene.add(directionalLight.target)

  if (fillLight) {
    fillLight.position.set(
      maxDimension * lighting.fill.position[0],
      maxDimension * lighting.fill.position[1],
      maxDimension * lighting.fill.position[2],
    )
    fillLight.target.position.copy(environmentCenter)
    scene.add(fillLight.target)
  }
}

const applySceneVisualTheme = (themeName, animateBackground = true) => {
  const sceneTheme = getSceneTheme(themeName)
  lighting = getSceneLighting(props.mode, themeName)

  if (!scene) return

  if (!isOverview) {
    scene.background = null
    renderer?.setClearColor(0x000000, 0)
    backgroundTransition = null
  } else if (animateBackground && scene.background?.isColor) {
    backgroundTransition = {
      from: scene.background.clone(),
      to: new THREE.Color(lighting.background),
      startedAt: performance.now(),
    }
  } else {
    scene.background = new THREE.Color(lighting.background)
    backgroundTransition = null
  }

  if (renderer) renderer.toneMappingExposure = lighting.toneMappingExposure

  if (hemisphereLight) {
    hemisphereLight.color.setHex(lighting.hemisphere.skyColor)
    hemisphereLight.groundColor.setHex(lighting.hemisphere.groundColor)
    hemisphereLight.intensity = lighting.hemisphere.intensity
  }

  if (ambientLight) {
    ambientLight.color.setHex(lighting.ambient.color)
    ambientLight.intensity = lighting.ambient.intensity
  }

  if (directionalLight) {
    directionalLight.color.setHex(lighting.key.color)
    directionalLight.intensity = lighting.key.intensity
  }

  if (fillLight) {
    fillLight.color.setHex(lighting.fill.color)
    fillLight.intensity = lighting.fill.intensity
  }

  if (environmentBounds) updateSceneLighting()
  if (isOverview && environmentGroup) {
    updateOverviewMaterialTheme(environmentGroup, sceneTheme.overview)
  }
}

const updateBackgroundTransition = (time) => {
  if (!backgroundTransition || !scene?.background?.isColor) return

  const progress = Math.min((time - backgroundTransition.startedAt) / 350, 1)
  const easedProgress = progress * progress * (3 - 2 * progress)
  scene.background.lerpColors(
    backgroundTransition.from,
    backgroundTransition.to,
    easedProgress,
  )

  if (progress >= 1) backgroundTransition = null
}

const makeOverviewPreset = () => ({
  position: camera.position.toArray(),
  target: controls.target.toArray(),
  zoom: camera.zoom,
  quaternion: camera.quaternion.toArray(),
  positionOffset: camera.position.clone().sub(environmentCenter).toArray(),
  targetOffset: controls.target.clone().sub(environmentCenter).toArray(),
})

const applyOverviewCameraPreset = (preset = DEFAULT_OVERVIEW_CAMERA_PRESET) => {
  if (!isOverview || !environmentCenter || !isOverviewCameraPreset(preset)) return false

  camera.position.copy(environmentCenter).add(new THREE.Vector3(...preset.positionOffset))
  camera.zoom = preset.zoom
  camera.updateProjectionMatrix()

  const target = environmentCenter.clone().add(new THREE.Vector3(...preset.targetOffset))
  controls.target.copy(target)
  camera.lookAt(target)
  controls.update()
  return true
}

const getActiveOverviewCameraPreset = () => (
  readStoredOverviewCameraPreset() || DEFAULT_OVERVIEW_CAMERA_PRESET
)

const logOverviewCameraPreset = () => {
  if (!cameraDebugEnabled || !environmentCenter) return

  const preset = makeOverviewPreset()
  console.log('OVERVIEW_CAMERA_PRESET', JSON.stringify(preset, null, 2))
  storeOverviewCameraPreset(preset)
}

const makeRealtimeMapCameraPreset = () => ({
  position: camera.position.toArray(),
  target: controls.target.toArray(),
  zoom: camera.zoom,
  quaternion: camera.quaternion.toArray(),
  positionOffset: camera.position.clone().sub(environmentCenter).toArray(),
  targetOffset: controls.target.clone().sub(environmentCenter).toArray(),
})

const applyRealtimeMapCameraPreset = (preset, animate = false) => {
  if (isOverview || !environmentCenter || !isRealtimeMapCameraPreset(preset)) return false
  const position = environmentCenter.clone().add(new THREE.Vector3(...preset.positionOffset))
  const target = environmentCenter.clone().add(new THREE.Vector3(...preset.targetOffset))
  camera.zoom = preset.zoom
  camera.updateProjectionMatrix()
  if (animate) {
    cameraFocusTransition = {
      elapsed: 0,
      duration: 1.8,
      startPosition: camera.position.clone(),
      startTarget: controls.target.clone(),
      endPosition: position,
      endTarget: target,
    }
    return true
  }
  camera.position.copy(position)
  controls.target.copy(target)
  camera.lookAt(target)
  controls.update()
  return true
}

const getActiveRealtimeMapCameraPreset = () => {
  if (!mapCameraDebugEnabled) return DEFAULT_REALTIME_MAP_CAMERA_PRESET
  return readStoredRealtimeMapCameraPreset() || DEFAULT_REALTIME_MAP_CAMERA_PRESET
}

const logRealtimeMapCameraPreset = () => {
  if (!mapCameraDebugEnabled || !environmentCenter) return

  const preset = makeRealtimeMapCameraPreset()
  console.log('REALTIME_MAP_CAMERA_PRESET', JSON.stringify(preset, null, 2))
  storeRealtimeMapCameraPreset(preset)
}

const fitPerspectiveCameraToModel = () => {

  const bounds = environmentBounds
  const size = bounds.getSize(new THREE.Vector3())
  const maxDimension = Math.max(size.x, size.y, size.z)
  const viewDirection = isOverview
    ? new THREE.Vector3(0, 0.72, 1).normalize()
    : new THREE.Vector3(1, 0.72, 1).normalize()
  const sphere = bounds.getBoundingSphere(new THREE.Sphere())
  const verticalFov = THREE.MathUtils.degToRad(camera.fov)
  const horizontalFov = 2 * Math.atan(Math.tan(verticalFov / 2) * camera.aspect)
  const limitingFov = Math.min(verticalFov, horizontalFov)
  const cameraDistance = (sphere.radius / Math.sin(limitingFov / 2)) * 1.02

  camera.position.copy(environmentCenter).addScaledVector(viewDirection, cameraDistance)
  camera.lookAt(environmentCenter)
  camera.near = Math.max(maxDimension * 0.001, 0.01)
  camera.far = cameraDistance + maxDimension * 4
  camera.updateProjectionMatrix()

  controls.target.copy(environmentCenter)
  controls.update()
}

const initializeOverviewCamera = () => {
  const size = environmentBounds.getSize(new THREE.Vector3())
  const maxDimension = Math.max(size.x, size.y, size.z)

  camera.near = Math.max(maxDimension * 0.001, 0.01)
  camera.far = maxDimension * 10
  applyOverviewCameraPreset(getActiveOverviewCameraPreset())
}

const createSceneLayers = () => {
  environmentGroup = new THREE.Group()
  environmentGroup.name = 'environmentGroup'

  actorGroup = new THREE.Group()
  actorGroup.name = 'actorGroup'

  robotGroup = new THREE.Group()
  robotGroup.name = 'robotGroup'
  robotGroup.visible = false

  characterGroup = new THREE.Group()
  characterGroup.name = 'characterGroup'
  characterGroup.visible = false

  overlayGroup = new THREE.Group()
  overlayGroup.name = 'overlayGroup'
  overlayGroup.visible = false

  scene.add(environmentGroup, actorGroup, robotGroup, characterGroup, overlayGroup)
}

const initializeBaymaxActorsFromGraph = async () => {
  const page = isOverview ? 'overview' : 'realtimeMap'
  const response = await fetch(graphActorConfig.graphUrl, { cache: 'no-store' })
  if (!response.ok) throw new Error(`Graph 1 JSON 載入失敗（HTTP ${response.status}），Baymax 已停止移動。`)
  const navigation = await response.json()
  if (disposed) return
  const { topology, definitions: actorDefinitions } = buildGraphActorPlan(navigation, graphActorConfig)
  console.info('Baymax full Graph 1 connected components:', {
    source: navigation.sourceNavigationGraph,
    graphIndex: navigation.graphIndex,
    graphVertices: navigation.vertices.length,
    graphLanes: navigation.lanes.length,
    componentCount: topology.components.length,
    components: topology.componentDetails.map((component, index) => ({
      index,
      vertices: component.ids,
      lanes: component.laneCount,
    })),
  })
  console.table(actorDefinitions.map((definition) => ({
    actor: definition.name,
    seed: definition.seed,
    graph: 'Graph 1',
    component: definition.componentIndex,
    startVertex: definition.startVertexId,
    worldPosition: definition.point.toArray().join(', '),
  })))

  baymaxControllers = actorDefinitions.map((definition, index) => {
    const wrapper = new THREE.Group()
    wrapper.name = `${definition.name} ActorMotionWrapper`
    actorGroup.add(wrapper)

    const controller = new BaymaxNurseController({
      actorGroup: wrapper,
      config: baymaxConfig,
      animationOffset: definition.animationOffset,
      name: definition.name,
    })
    controller.setVisible(actorVisibility[page])
    controller.load().catch((error) => {
      if (disposed) return
      console.error(`${definition.name} GLB load failed:`, error)
      controller.dispose()
    })
    return controller
  })
  graphActorCoordinator = new GraphActorCoordinator({
    topology,
    definitions: actorDefinitions,
    controllers: baymaxControllers,
    config: graphActorConfig,
  })
}

const focusRealtimeLocation = (point) => {
  if (isOverview || !controls || !camera) return
  const offset = camera.position.clone().sub(controls.target)
  const distance = THREE.MathUtils.clamp(offset.length(), 8, 18)
  cameraFocusTransition = {
    elapsed: 0,
    duration: 1.8,
    startPosition: camera.position.clone(),
    startTarget: controls.target.clone(),
    endTarget: point.clone(),
    endPosition: point.clone().add(offset.normalize().multiplyScalar(distance)),
  }
}

const updateCameraFocus = (delta) => {
  if (!cameraFocusTransition) return
  cameraFocusTransition.elapsed += delta
  const progress = Math.min(cameraFocusTransition.elapsed / cameraFocusTransition.duration, 1)
  const eased = progress * progress * (3 - 2 * progress)
  camera.position.lerpVectors(cameraFocusTransition.startPosition, cameraFocusTransition.endPosition, eased)
  controls.target.lerpVectors(cameraFocusTransition.startTarget, cameraFocusTransition.endTarget, eased)
  camera.lookAt(controls.target)
  if (progress >= 1) cameraFocusTransition = null
}

const updateRealtimeFollowCamera = (delta) => {
  if (isOverview || cameraMode.value === 'global' || !followRobotId.value || cameraFocusTransition) return
  const position = navigationLayer?.getRobotPosition(followRobotId.value)
  const forward = navigationLayer?.getRobotForward(followRobotId.value)
  if (!position || !forward || forward.lengthSq() < 0.5) return
  const alpha = 1 - Math.exp(-5 * delta)
  const pose = getRobotCameraPose(cameraMode.value, position, forward)
  if (!pose) return
  camera.position.lerp(pose.position, alpha)
  controls.target.lerp(pose.target, alpha)
  camera.lookAt(controls.target)
}

const toggleMapTool = (id) => {
  if (id === 'tasks') { showRunningTasks.value = !showRunningTasks.value; return }
  activeMapTool.value = activeMapTool.value === id ? null : id
}
const resetOverviewView = () => {
  if (!environmentCenter) return
  applyOverviewCameraPreset(getActiveOverviewCameraPreset())
}
const setCameraMode = (mode) => {
  if (mode === 'global') {
    cameraMode.value = 'global'
    followRobotId.value = null
    navigationLayer?.setFollowingRobot(null)
    cameraMenuOpen.value = false
    if (controls) controls.enabled = true
    applyRealtimeMapCameraPreset(getActiveRealtimeMapCameraPreset(), true)
    return
  }
  if (!selectedRobotId.value) return
  cameraMode.value = mode
  followRobotId.value = selectedRobotId.value
  navigationLayer?.setFollowingRobot(followRobotId.value)
  cameraFocusTransition = null
  if (controls) controls.enabled = false
  cameraMenuOpen.value = false
}
const resetRealtimeFocus = () => {
  selectedRobotId.value = null
  realtimeSelectedTaskId.value = null
  followRobotId.value = null
  cameraMode.value = 'global'
  cameraMenuOpen.value = false
  cameraFocusTransition = null
  showRobots.value = true
  showActiveRoute.value = true
  showRouteArrows.value = true
  priorityFilters.value = { emergency: true, high: true, normal: true, low: true }
  isolatePriorities.value = false
  navigationLayer?.setPreviewRoute(null)
  navigationLayer?.setSelectedRobot(null)
  navigationLayer?.setFollowingRobot(null)
  navigationLayer?.setRobotsVisible(true)
  navigationLayer?.setActiveVisible(true)
  navigationLayer?.setArrowsVisible(true)
  locationMarkerLayer?.setSelectedRobot(null)
  if (controls) controls.enabled = true
  applyRealtimeMapCameraPreset(getActiveRealtimeMapCameraPreset(), true)
}
const selectRobot = (id) => {
  if (cameraMode.value !== 'global') setCameraMode('global')
  selectedRobotId.value = id
  realtimeSelectedTaskId.value = mapStore.tasks.value.find((task) => task.robotId === id && task.status === 'executing')?.id || null
  navigationLayer?.setPreviewRoute(null)
  navigationLayer?.setSelectedRobot(id)
  locationMarkerLayer?.setSelectedRobot(id)
  if (id) activeMapTool.value = 'robots'
}
const toggleRobotFollowing = () => {
  if (followRobotId.value === activeRobotId.value) setCameraMode('global')
  else {
    selectedRobotId.value = activeRobotId.value
    setCameraMode('thirdPerson')
  }
}
const taskDirectionLabel = (task) => task?.direction === 'return' ? '回程' : '去程'
const robotCssColor = (id) => `#${new THREE.Color(robotRouteColors[id]?.main || colorHex(visualTokens.neutral)).getHexString()}`
const previewQueuedTask = (task) => {
  if (!navigationData.value) return
  realtimeSelectedTaskId.value = task.id
  const preview = buildLiveMapRoutes(navigationData.value, [{ ...task, status: 'executing' }])[0]
  navigationLayer?.setPreviewRoute(preview || null)
}
const robotDisplayState = (robot) => {
  if (robot?.state === 'offline' && mapStore.tasks.value.some(task => task.robotId === robot.id && task.isSimulated && task.status === 'executing'))
    return t('liveMap.simulatedMovement')
  return t(`robotStatus.states.${robot?.state || 'unknown'}`)
}
const applyPriorityFilter = () => {
  navigationLayer?.setPriorityFilter(selectedPriorities.value, isolatePriorities.value)
  locationMarkerLayer?.setPriorityFilter(selectedPriorities.value, isolatePriorities.value)
}

const findRobotAtPointer = (event) => {
  if (isOverview || !renderer || !camera || !navigationLayer) return null
  const rect = renderer.domElement.getBoundingClientRect()
  pointerNdc.set(
    ((event.clientX - rect.left) / rect.width) * 2 - 1,
    -((event.clientY - rect.top) / rect.height) * 2 + 1,
  )
  robotRaycaster.setFromCamera(pointerNdc, camera)
  const hit = robotRaycaster.intersectObjects(navigationLayer.getRobotPickables(), false)[0]?.object
  let target = hit
  while (target && !target.userData.robotId) target = target.parent
  return target?.userData.robotId || null
}

const onScenePointerDown = (event) => {
  pointerStart = { x: event.clientX, y: event.clientY }
  pointerDragged = false
}

const onScenePointerMove = (event) => {
  if (pointerStart) {
    const distance = Math.hypot(event.clientX - pointerStart.x, event.clientY - pointerStart.y)
    if (distance >= 5) pointerDragged = true
    if (distance >= 12 && followRobotId.value) setCameraMode('global')
  }
  const robotId = findRobotAtPointer(event)
  renderer.domElement.style.cursor = robotId && !pointerDragged ? 'pointer' : (pointerStart ? 'grabbing' : 'grab')
}

const onScenePointerUp = (event) => {
  if (!pointerDragged) {
    const robotId = findRobotAtPointer(event)
    if (robotId) selectRobot(robotId)
  }
  pointerStart = null
  pointerDragged = false
}

const onScenePointerLeave = () => {
  pointerStart = null
  pointerDragged = false
  if (renderer) renderer.domElement.style.cursor = 'grab'
}

const initializeRmfNavigation = async () => {
  if (disposed) return
  const response = await fetch(NAVIGATION_ASSETS.graph0, { cache: 'no-store' })
  if (!response.ok) throw new Error(`RMF navigation JSON load failed: ${response.status}`)
  const data = await response.json()
  if (disposed) return
  navigationData.value = data
  const tasks = isOverview ? mapStore.tasks.value : floorTasks.value
  const routes = isOverview ? buildActiveRoutes(data,tasks) : buildLiveMapRoutes(data,tasks)
  const displayedRoutes = isOverview ? routes.slice(0, 1) : routes
  const robotWaypoints = Object.fromEntries(mapStore.robots.value.map((robot) => [
    robot.id,
    robot.currentWaypoint || demoRobotWaypoints[robot.id] || robot.chargingWaypoint,
  ]))
  navigationLayer = new RmfNavigationLayer({
    data,
    parent: scene,
    routes: displayedRoutes,
    robots: mapStore.robots.value,
    robotWaypoints,
    camera,
    overview: isOverview,
    showRobotModels: false,
  })
  navigationLayer.setBaseVisible(!isOverview && showNavigation.value)
  navigationLayer.setActiveVisible(showActiveRoute.value)
  navigationLayer.setRobotsVisible(!isOverview && showRobots.value)
  if (isOverview) return
  doorController = new RmfDoorController({ model: environmentGroup, doors: data.doors, doorNames: data.doors.map((door) => door.name) })
  navigationLayer.doorController = doorController
  roomLabelLayer = new RoomLabelLayer({ data, container: container.value, camera, canvas: renderer.domElement, translate: translateLocation })
  roomLabelLayer.setVisible(showRoomLabels.value)
  locationMarkerLayer = new LocationMarkerLayer({
    data,
    details: buildLiveMapLocationDetails(data,floorTasks.value,floorRobots.value),
    parent: scene,
    container: container.value,
    camera,
    canvas: renderer.domElement,
    environmentGroup,
    translate: translateLocation,
  })
  locationMarkerLayer.setVisible(showLocations.value)
  locationMarkerLayer.setLabelsVisible(showTaskLabels.value)
  locationMarkerLayer.setRoomLabelsVisible(showRoomLabels.value)
  syncLiveMap()
  applyPriorityFilter()
  if (mapAlignmentDebugEnabled) {
    mapAlignmentDebug = new MapAlignmentDebug({
      camera,
      canvas: renderer.domElement,
      environmentGroup,
      scene,
      vertices: data.vertices,
      selectedId: alignmentVertexId.value,
    })
    console.info('Map alignment debug enabled. Select an RMF vertex, then click its matching floor point. Use at least three pairs.')
  }
  console.info('RMF navigation loaded:', {
    source: data.sourceNavigationGraph,
    levels: data.levels.map((level) => level.id),
    vertices: data.vertices.length,
    lanes: data.lanes.length,
    namedWaypoints: data.namedWaypoints.length,
    chargingWaypoints: data.chargingWaypoints.length,
    doors: data.doors.length,
    lifts: Object.keys(data.lifts).length,
  })
}

const moveCollisionProxiesToHiddenLayer = (model) => {
  const proxies = []

  model.traverse((object) => {
    if (!object.isMesh || !String(object.name).toLowerCase().endsWith('__proxy')) return

    const materials = Array.isArray(object.material) ? object.material : [object.material]
    const hasNamedMaterial = materials.some((material) => String(material?.name).trim())
    if (!hasNamedMaterial) proxies.push(object)
  })

  scene.updateMatrixWorld(true)
  proxies.forEach((proxy) => overlayGroup.attach(proxy))

  if (proxies.length > 0) {
    console.info(`Hidden ${proxies.length} collision proxy meshes.`)
  }
}

const moveEmbeddedDynamicAssetsToHiddenLayers = (model) => {
  const matches = []

  model.traverse((object) => {
    const layer = getEmbeddedAssetLayer(object.name)
    if (layer) matches.push({ object, layer })
  })

  scene.updateMatrixWorld(true)

  const hiddenObjectNames = []
  for (const { object, layer } of matches) {
    object.traverse((child) => hiddenObjectNames.push(child.name))

    if (layer === 'robots') {
      robotGroup.attach(object)
    } else {
      characterGroup.attach(object)
    }
  }

  if (hiddenObjectNames.length > 0) {
    console.info('Hidden embedded dynamic scene objects:', hiddenObjectNames)
  }

  return hiddenObjectNames
}

const stabilizeDoorSurfaces = (model) => {
  model.traverse((object) => {
    if (
      !object.isMesh
      || !/(?:door|main_entrance).*__proxy$/i.test(String(object.name))
    ) return

    const materials = Array.isArray(object.material) ? object.material : [object.material]
    materials.forEach((material) => {
      if (!material) return
      material.polygonOffset = true
      material.polygonOffsetFactor = -1
      material.polygonOffsetUnits = -1
      material.needsUpdate = true
    })
    object.renderOrder = 1
  })
}

const createScene = () => {
  scene = new THREE.Scene()
  scene.background = isOverview ? new THREE.Color(lighting.background) : null
  createSceneLayers()

  camera = new THREE.PerspectiveCamera(42, 1, 0.01, 10000)

  renderer = new THREE.WebGLRenderer({
    antialias: true,
    alpha: true,
    powerPreference: 'high-performance',
  })
  if (!isOverview) renderer.setClearColor(0x000000, 0)
  renderer.outputColorSpace = THREE.SRGBColorSpace
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = lighting.toneMappingExposure
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = THREE.PCFSoftShadowMap
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  const sceneDescription = () => t(cameraDebugEnabled || !isOverview ? 'liveMap.sceneDescription' : 'liveMap.fixedSceneDescription')
  renderer.domElement.setAttribute('aria-label', sceneDescription())
  container.value.appendChild(renderer.domElement)

  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.075
  controls.enabled = !isOverview
  controls.enablePan = !isOverview
  controls.enableZoom = !isOverview
  controls.enableRotate = !isOverview
  controls.screenSpacePanning = !isOverview
  if (cameraDebugEnabled) controls.addEventListener('end', logOverviewCameraPreset)
  if (mapCameraDebugEnabled) controls.addEventListener('end', logRealtimeMapCameraPreset)
  if (!isOverview) {
    renderer.domElement.addEventListener('pointerdown', onScenePointerDown)
    renderer.domElement.addEventListener('pointermove', onScenePointerMove)
    renderer.domElement.addEventListener('pointerup', onScenePointerUp)
    renderer.domElement.addEventListener('pointerleave', onScenePointerLeave)
  }

  hemisphereLight = new THREE.HemisphereLight(
    lighting.hemisphere.skyColor,
    lighting.hemisphere.groundColor,
    lighting.hemisphere.intensity,
  )
  scene.add(hemisphereLight)

  ambientLight = new THREE.AmbientLight(lighting.ambient.color, lighting.ambient.intensity)
  scene.add(ambientLight)

  directionalLight = new THREE.DirectionalLight(lighting.key.color, lighting.key.intensity)
  directionalLight.castShadow = lighting.key.castShadow
  directionalLight.shadow.mapSize.set(2048, 2048)
  scene.add(directionalLight)

  fillLight = new THREE.DirectionalLight(lighting.fill.color, lighting.fill.intensity)
  fillLight.castShadow = false
  scene.add(fillLight)

  updateRendererSize()
  resizeObserver = new ResizeObserver(updateRendererSize)
  resizeObserver.observe(container.value)
}

const loadModel = () => {
  const loader = createGltfLoader()

  loader.load(
    runtimeModelUrl(props.modelUrl),
    (gltf) => {
      if (disposed) {
        disposeObject(gltf.scene)
        return
      }

      try {
        const environmentModel = gltf.scene
        environmentGroup.add(environmentModel)
        if (props.mode === 'overview') {
          const materialRows = collectOverviewMeshMaterialRows(environmentModel)
          moveCollisionProxiesToHiddenLayer(environmentModel)
          moveEmbeddedDynamicAssetsToHiddenLayers(environmentModel)
          if (import.meta.env.DEV) {
            console.table(materialRows)
            console.table(
              materialRows.filter(({ object, material }) => (
                `${object} ${material}`.toLowerCase().includes('reception')
              )),
            )
            console.info(
              'Overview warm architectural accents:',
              materialRows.filter(({ category }) => (
                category === 'woodAccent' || category === 'woodAccentDark'
              )),
            )
          }
          const classifications = applyOverviewMaterials(
            environmentGroup,
            getSceneTheme(props.theme).overview,
          )
          console.info('Overview material classifications:', classifications)
        }
        stabilizeDoorSurfaces(environmentModel)

        environmentGroup.traverse((child) => {
          if (!child.isMesh) return
          child.castShadow = true
          child.receiveShadow = true
        })

        prepareModelBounds(environmentGroup)
        updateSceneLighting()
        if (isOverview) {
          actorGroup.visible = false
          initializeOverviewCamera()
        } else {
          initializeBaymaxActorsFromGraph().catch((error) => {
            if (disposed) return
            actorGroup.visible = false
            actorErrorMessage.value = error instanceof Error ? error.message : 'Graph 1 初始化失敗，Baymax 已停止移動。'
            console.error('Baymax Graph 1 initialization failed:', error)
          })
          fitPerspectiveCameraToModel()
          applyRealtimeMapCameraPreset(getActiveRealtimeMapCameraPreset())
          initializeRmfNavigation().catch((error) => console.error(error))
        }
        progress.value = 100
        loading.value = false
      } catch (error) {
        errorMessage.value = error instanceof Error ? error.message : '模型初始化失敗。'
        loading.value = false
      }
    },
    (event) => {
      if (event.total > 0) {
        progress.value = Math.min(Math.round((event.loaded / event.total) * 100), 99)
      }
    },
    (error) => {
      console.error('Hospital GLB load failed:', error)
      errorMessage.value = `無法載入醫院模型：${props.modelUrl}。請確認檔案存在、Vite public 路徑正確，並檢查瀏覽器 Network 與 Console。`
      loading.value = false
    },
  )
}

const animate = (time = performance.now()) => {
  if (disposed) return

  animationFrameId = requestAnimationFrame(animate)
  const delta = sceneClock.getDelta()
  updateBackgroundTransition(time)
  if (graphActorCoordinator) graphActorCoordinator.update(delta)
  else baymaxControllers.forEach((controller) => controller.update(delta))
  navigationLayer?.update(delta)
  completeArrivedSimulations()
  if (doorController) doorController.update(delta, mapStore.robots.value.map((robot) => navigationLayer?.getRobotPosition(robot.id)))
  if (locationMarkerLayer) {
    const robotPositions = new Map(mapStore.robots.value.map((robot) => [
      robot.id,
      navigationLayer?.getRobotPosition(robot.id),
    ]))
    const routeStates = new Map(mapStore.robots.value.map((robot) => [
      robot.id,
      navigationLayer?.getRobotRouteState(robot.id),
    ]))
    locationMarkerLayer.setDestinationState(mapStore.tasks.value, robotPositions, routeStates)
  }
  updateRealtimeFollowCamera(delta)
  if (!isOverview && activeRobotId.value) {
    const anchor = navigationLayer?.getRobotInfoAnchor(activeRobotId.value)
    if (anchor) {
      const projected = anchor.project(camera)
      const rect = renderer.domElement.getBoundingClientRect()
      const cardWidth = 170
      const cardHeight = 94
      const margin = 16
      const navbarHeight = 64
      const projectedX = (projected.x * 0.5 + 0.5) * rect.width
      const projectedY = (-projected.y * 0.5 + 0.5) * rect.height
      const overlayX = projectedX
      const overlayY = projectedY - 12
      followWindow.value = {
        visible: projected.z >= -1 && projected.z <= 1,
        x: THREE.MathUtils.clamp(overlayX, margin + cardWidth / 2, rect.width - margin - cardWidth / 2),
        y: THREE.MathUtils.clamp(overlayY, navbarHeight + margin + cardHeight, rect.height - margin),
      }
    }
  } else followWindow.value = { ...followWindow.value, visible: false }
  updateCameraFocus(delta)
  controls.update()
  locationMarkerLayer?.update(time / 1000)
  roomLabelLayer?.setSuppressedLabels(locationMarkerLayer?.getVisibleTaskLabels() || [])
  roomLabelLayer?.update()
  renderer.render(scene, camera)
}

onMounted(() => {
  createScene()
  loadModel()
  sceneClock.start()
  animate()
})

watch(
  () => props.theme,
  (theme) => applySceneVisualTheme(theme),
)

watch(showNavigation, (visible) => navigationLayer?.setBaseVisible(visible))
watch(showActiveRoute, (visible) => navigationLayer?.setActiveVisible(visible))
watch(showLocations, (visible) => locationMarkerLayer?.setVisible(visible))
watch(showActors, (visible) => { if (actorGroup) actorGroup.visible = visible })
watch(showRobots, (visible) => navigationLayer?.setRobotsVisible(visible))
watch(showTaskLabels, (visible) => locationMarkerLayer?.setLabelsVisible(visible))
watch(showRoomLabels, (visible) => { roomLabelLayer?.setVisible(visible); locationMarkerLayer?.setRoomLabelsVisible(visible) })
watch(locale, () => {
  roomLabelLayer?.setTranslation(translateLocation)
  locationMarkerLayer?.setTranslation(translateLocation)
  renderer?.domElement?.setAttribute('aria-label', t(cameraDebugEnabled || !isOverview ? 'liveMap.sceneDescription' : 'liveMap.fixedSceneDescription'))
})
watch(showRouteArrows, (visible) => navigationLayer?.setArrowsVisible(visible))
watch(alignmentVertexId, (id) => mapAlignmentDebug?.setSelectedId(id))
watch([priorityFilters, isolatePriorities], applyPriorityFilter, { deep: true })
const syncLiveMap = () => {
  if (!navigationData.value || !navigationLayer) return
  const routes = buildLiveMapRoutes(navigationData.value,floorTasks.value)
  const signature = JSON.stringify(routes.map(route=>[route.id,route.robotId,route.priority,route.vertexIds]))
  if (signature !== liveNavigationSignature) { navigationLayer.setRoutes(routes); liveNavigationSignature=signature }
  const simulatedRobotIds = new Set(routes.filter(route => route.isSimulated).map(route => route.robotId))
  const displayRobots = simulatedRobotIds.size
    ? placeSimulatedRobotsAtRouteStart(
      withPreviewPositions(floorRobots.value.filter(robot => robot.hasPose || simulatedRobotIds.has(robot.id)),
        navigationData.value, previewPlacements), routes, navigationData.value)
    : floorRobots.value
  navigationLayer.setLiveRobots(displayRobots,routes)
  navigationLayer.setSelectedRobot(selectedRobotId.value)
  navigationLayer.setFollowingRobot(followRobotId.value)
  locationMarkerLayer?.setDetails(buildLiveMapLocationDetails(navigationData.value,floorTasks.value,floorRobots.value))
  locationMarkerLayer?.setVisible(showLocations.value)
  locationMarkerLayer?.setLabelsVisible(showTaskLabels.value)
  applyPriorityFilter()
}
watch([()=>mapStore.tasks.value,()=>mapStore.robots.value,activeFloor],()=>{
  if (!isOverview) syncLiveMap()
}, {deep:true})
onMounted(()=>{ if (!isOverview) { refreshLiveMap(); livePollTimer=window.setInterval(refreshLiveMap,5000); document.addEventListener('pointerdown',onFloorPickerOutside) } })

onActivated(() => {
  if (!environmentCenter) return

  if (isOverview) {
    applyOverviewCameraPreset(getActiveOverviewCameraPreset())
  } else {
    applyRealtimeMapCameraPreset(getActiveRealtimeMapCameraPreset())
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown',onFloorPickerOutside)
  disposed = true
  window.clearInterval(livePollTimer)
  cancelAnimationFrame(animationFrameId)
  sceneClock.stop()
  resizeObserver?.disconnect()
  if (cameraDebugEnabled) controls?.removeEventListener('end', logOverviewCameraPreset)
  if (mapCameraDebugEnabled) controls?.removeEventListener('end', logRealtimeMapCameraPreset)
  if (!isOverview && renderer?.domElement) {
    renderer.domElement.removeEventListener('pointerdown', onScenePointerDown)
    renderer.domElement.removeEventListener('pointermove', onScenePointerMove)
    renderer.domElement.removeEventListener('pointerup', onScenePointerUp)
    renderer.domElement.removeEventListener('pointerleave', onScenePointerLeave)
  }
  controls?.dispose()
  mapAlignmentDebug?.dispose()
  locationMarkerLayer?.dispose()
  roomLabelLayer?.dispose()
  doorController?.dispose()
  navigationLayer?.dispose()
  graphActorCoordinator?.dispose()
  baymaxControllers.forEach((controller) => controller.dispose())
  disposeOverviewMaterials(environmentGroup)
  disposeObject(environmentGroup)
  disposeObject(robotGroup)
  disposeObject(characterGroup)
  disposeObject(overlayGroup)
  disposeObject(actorGroup)

  if (directionalLight?.shadow?.map) {
    directionalLight.shadow.map.dispose()
  }

  renderer?.renderLists?.dispose()
  renderer?.dispose()
  renderer?.forceContextLoss()
  renderer?.domElement?.remove()

  scene?.clear()
  environmentGroup = null
  actorGroup = null
  robotGroup = null
  characterGroup = null
  overlayGroup = null
  mapAlignmentDebug = null
  locationMarkerLayer = null
  roomLabelLayer = null
  doorController = null
  navigationLayer = null
  graphActorCoordinator = null
  baymaxControllers = []
  hemisphereLight = null
  ambientLight = null
  fillLight = null
  controls = null
  renderer = null
  camera = null
  scene = null
})
</script>

<template>
  <section
    ref="container"
    class="hospital-scene"
    :class="{
      'hospital-scene--interactive': cameraDebugEnabled || !isOverview,
      'hospital-scene--realtime': !isOverview,
      'hospital-scene--unavailable-floor': !isOverview && activeFloor !== 1,
      'hospital-scene--dark': !isOverview && theme === 'dark',
    }"
  >
    <SharedLoading :loading="loading" :detail="progress > 0 ? `${progress}%` : '準備模型中…'" :error="errorMessage" error-title="場景載入失敗" />

    <div v-if="actorErrorMessage" class="actor-graph-error" role="alert">
      <strong>Baymax 已停止</strong>
      <span>{{ actorErrorMessage }}</span>
    </div>

    <template v-if="!isOverview">
      <div v-if="liveMapError" class="live-map-data-notice" role="alert"><span>{{liveMapError}}</span><button type="button" :disabled="liveMapLoading" @click="refreshLiveMap">{{t('common.retry')}}</button></div>
      <div v-if="activeFloor !== 1" class="floor-unavailable" role="status"><strong>{{ activeFloor }} 樓</strong><p>尚未提供此樓層的地圖與路網</p></div>
      <nav class="map-tool-rail" aria-label="即時地圖工具列">
        <button
          v-for="tool in mapTools"
          :key="tool.id"
          type="button"
          :class="{ 'is-active': tool.id === 'tasks' ? showRunningTasks : activeMapTool === tool.id }"
          :aria-label="tool.label"
          @click="toggleMapTool(tool.id)"
        >
          <component :is="tool.icon" :size="17" :stroke-width="1.7" />
        </button>
        <div ref="floorPicker" class="map-floor-picker">
          <button type="button" class="floor-trigger" :aria-label="t('map.selectFloor')" aria-haspopup="menu" :aria-expanded="floorMenuOpen" @click="floorMenuOpen ? closeFloorMenu() : openFloorMenu()" @keydown.down.prevent="openFloorMenu" @keydown.up.prevent="openFloorMenu">F{{ activeFloor }}</button>
          <div v-if="floorMenuOpen" class="floor-options" role="menu" :aria-label="t('map.selectFloor')" @keydown="handleFloorMenuKeydown">
            <button v-for="floor in floorOptions" :key="floor" type="button" class="floor-option" role="menuitemradio" :aria-checked="activeFloor === floor" @click="selectFloor(floor)">F{{ floor }}</button>
          </div>
          <button type="button" :aria-label="t('map.zoomIn')" @click="zoomRealtimeMap(0.8)"><Plus :size="19" /></button>
          <button type="button" :aria-label="t('map.zoomOut')" @click="zoomRealtimeMap(1.25)"><Minus :size="19" /></button>
        </div>
        <span class="map-tool-rail__divider"></span>
        <button type="button" aria-label="恢復全域視角" @click="resetRealtimeFocus">
          <RotateCcw :size="17" :stroke-width="1.7" />
        </button>
      </nav>

      <aside v-if="showRunningTasks" class="map-tool-drawer map-running-tasks" :aria-label="t('liveMap.runningRobotInfo')">
        <header><strong>{{ t('liveMap.activeTasks') }} · F{{ activeFloor }}</strong><button type="button" :aria-label="t('liveMap.collapseActiveTasks')" @click="showRunningTasks = false"><X :size="16" /></button></header>
        <div class="map-task-list">
          <article v-for="task in floorTasks" :key="task.id" class="running-task-item" :style="{ '--robot-color': robotCssColor(task.robotId) }">
            <span class="running-task-copy">
              <span class="running-task-title"><span>{{ task.taskCode || task.id }}</span><strong>{{ translateTask(task.title) }}</strong><em v-if="task.isSimulated" class="simulation-mark">{{t('liveMap.simulated')}}</em></span>
              <small>{{ robotDisplayCode(task.robotId) }} · {{ translateLocation(task.source) }} → {{ translateLocation(task.destination) }}</small>
            </span>
          </article>
          <p v-if="!floorTasks.length">目前沒有執行中任務</p>
        </div>

      </aside>

      <aside
        v-if="activeMapTool"
        class="map-tool-drawer"
        :class="{ 'map-tool-drawer--robots': activeMapTool === 'robots' }"
        :aria-label="`${mapTools.find((tool) => tool.id === activeMapTool)?.label}面板`"
      >
        <header>
          <strong>{{ mapTools.find((tool) => tool.id === activeMapTool)?.label }}</strong>
          <button type="button" aria-label="關閉面板" @click="activeMapTool = null"><X :size="16" /></button>
        </header>

        <div v-if="activeMapTool === 'overview'" class="map-overview-summary">
          <div><span>機器人</span><strong>{{ floorRobots.length }} 台</strong></div>
          <div><span>執行中</span><strong>{{ floorTasks.length }} 任務</strong></div>
          <p v-if="liveMapLoading" role="status">{{t('common.loading')}}</p>
        </div>

        <div v-else-if="activeMapTool === 'robots'" class="map-robot-list">
          <div class="robot-segmented-filter" :aria-label="t('liveMap.robotStateFilter')">
            <button
              v-for="filter in [{ id: 'all', label: t('common.all') }, { id: 'busy', label: t('robotStatus.states.busy') }, { id: 'idle', label: t('robotStatus.states.idle') }]"
              :key="filter.id"
              type="button"
              :class="{ 'is-active': robotDrawerFilter === filter.id }"
              @click="robotDrawerFilter = filter.id"
            >
              {{ filter.label }} {{ robotDrawerCounts[filter.id] }}
            </button>
          </div>
          <button
            v-for="robot in filteredDrawerRobots"
            :key="robot.id"
            type="button"
            class="robot-list-row"
            :class="{ 'is-selected': selectedRobotId === robot.id, 'is-offline': robot.state === 'offline' || robot.state === 'error' }"
            :style="{ '--robot-color': robotCssColor(robot.id) }"
            @click="selectRobot(robot.id)"
          >
            <span class="robot-list-icon" aria-hidden="true"><Bot :size="16" :stroke-width="1.7" /></span>
            <span class="robot-list-identity">
              <strong>{{ robot.displayCode || robotDisplayCode(robot.id) }}</strong>
              <small>{{ robotDisplayState(robot) }}</small>
            </span>
            <strong class="robot-list-battery">{{ robot.battery == null ? '—' : `${robot.battery}%` }}</strong>
          </button>
          <p v-if="!filteredDrawerRobots.length" class="empty-task">{{ t('liveMap.noRobotsForFilter') }}</p>
          <section v-if="unlocatedRobots.length" class="unlocated-robot-list"><p>{{ t('liveMap.unknownFloor',{count:unlocatedRobots.length}) }}</p><div v-for="robot in unlocatedRobots" :key="robot.id">{{robotDisplayCode(robot.id)}}</div></section>
          <section v-if="selectedRobotId" class="selected-robot-tasks">
            <p class="drawer-section-label">{{ t('liveMap.currentRobotTask') }}</p>
            <article v-if="selectedActiveTask" class="robot-task-card is-active" :style="{ '--robot-color': robotCssColor(selectedRobotId) }">
              <strong>{{ selectedActiveTask.taskCode || selectedActiveTask.id }}　{{ translateTask(selectedActiveTask.title) }}</strong>
              <span>{{ translateLocation(dispatchWaypointLabels[selectedActiveTask.source] || selectedActiveTask.source) }} → {{ translateLocation(dispatchWaypointLabels[selectedActiveTask.destination] || selectedActiveTask.destination) }}</span>
              <small>{{ t(`priority.${normalizedPriority(selectedActiveTask.priority)}`) }}</small>
            </article>
            <p v-else class="empty-task">{{ t('liveMap.noRobotRunningTask') }}</p>
            <template v-if="selectedQueuedTasks.length">
              <p class="drawer-section-label">{{ t('liveMap.queuedRobotTasks') }}</p>
              <button v-for="task in selectedQueuedTasks" :key="task.id" type="button" class="queued-task" @click="previewQueuedTask(task)">
                <strong>{{ task.taskCode || task.id }}　{{ translateTask(task.title) }}</strong>
                <small>{{ task.startTime.slice(0, 5) }}・{{ t(`priority.${task.priority}`) }}</small>
              </button>
            </template>
          </section>
        </div>

        <div v-else class="map-layer-list">
          <p class="drawer-section-label">{{t('liveMap.visibleLayers')}}</p>
          <label><input v-model="showLocations" type="checkbox">{{t('liveMap.locationNodes')}}</label>
          <label><input v-model="showNavigation" type="checkbox">{{t('liveMap.baseGraph')}}</label>
          <label><input v-model="showActiveRoute" type="checkbox">{{t('liveMap.referenceRoute')}}</label>
          <label><input v-model="showRouteArrows" type="checkbox">{{t('liveMap.referenceArrows')}}</label>
          <label><input v-model="showTaskLabels" type="checkbox">{{t('liveMap.taskLabels')}}</label>
          <label><input v-model="showRoomLabels" type="checkbox">{{t('liveMap.roomLabels')}}</label>
          <label><input v-model="showActors" type="checkbox">{{t('liveMap.people')}}</label>
          <label><input v-model="showRobots" type="checkbox">{{t('liveMap.robots')}}</label>
          <fieldset class="priority-filter">
            <legend class="drawer-section-label">{{t('liveMap.taskPriority')}}</legend>
            <label v-for="priority in Object.keys(priorityOrder)" :key="priority">
              <input v-model="priorityFilters[priority]" :data-priority="priority" type="checkbox">{{ t(`priority.${priority}`) }}
            </label>
            <label class="priority-isolate"><input v-model="isolatePriorities" type="checkbox">{{t('liveMap.isolatePriorities')}}</label>
          </fieldset>
          <div v-if="mapAlignmentDebugEnabled && navigationData" class="alignment-debug-control">
            <span>對齊 Vertex</span>
            <select v-model="alignmentVertexId" aria-label="選擇 RMF Vertex">
              <option v-for="vertex in navigationData.vertices" :key="vertex.id" :value="vertex.id">{{ vertex.id }} · {{ vertex.name }}</option>
            </select>
            <small>選擇後點擊對應地板，至少記錄三點。</small>
          </div>
        </div>
      </aside>

      <aside
        v-if="followWindow.visible && selectedRobot"
        class="robot-info-card robot-mini-card"
        :class="{ 'is-following': followRobotId === activeRobotId }"
        :style="[
          robotInfoCardStyle,
          { transform: `translate3d(${followWindow.x}px, ${followWindow.y}px, 0) translate(-50%, -100%)` },
        ]"
      >
        <header class="robot-info-card__header">
          <strong>{{ selectedRobot.displayCode || robotDisplayCode(selectedRobot.id) }}</strong>
        </header>
        <p>{{ selectedRobot.battery == null ? '—' : `${selectedRobot.battery}%` }} · {{ robotDisplayState(selectedRobot) }}</p>
        <div class="robot-info-card__actions">
          <button type="button" @click="toggleRobotFollowing">
            <LocateFixed :size="13" />{{ followRobotId === activeRobotId ? t('liveMap.unfollow') : t('liveMap.follow') }}
          </button>
        </div>
      </aside>

      <div
        v-if="followRobotId"
        class="follow-camera-dock"
        :style="robotInfoCardStyle"
      >
        <div v-if="cameraMenuOpen" class="follow-camera-options" aria-label="跟隨視角">
          <button type="button" title="第一視角" aria-label="第一視角" :class="{ 'is-active': cameraMode === 'firstPerson' }" @click="setCameraMode('firstPerson')"><Eye :size="15" /></button>
          <button type="button" title="第三視角" aria-label="第三視角" :class="{ 'is-active': cameraMode === 'thirdPerson' }" @click="setCameraMode('thirdPerson')"><Orbit :size="15" /></button>
          <button type="button" title="局部跟隨" aria-label="局部跟隨" :class="{ 'is-active': cameraMode === 'localFollow' }" @click="setCameraMode('localFollow')"><LocateFixed :size="15" /></button>
        </div>
        <button type="button" class="follow-camera-trigger" title="切換跟隨視角" aria-label="切換跟隨視角" :aria-expanded="cameraMenuOpen" @click="cameraMenuOpen = !cameraMenuOpen"><Camera :size="16" /></button>
      </div>
    </template>
  </section>
</template>

<style scoped>
.map-floor-picker{position:relative;display:grid;gap:4px;justify-items:center;padding:5px 0;color:var(--map-muted);font-size:10px}
.map-running-tasks.map-tool-drawer{top:auto;bottom:18px;left:18px;width:min(340px,calc(100% - 36px));max-height:min(38%,340px)}
.floor-unavailable{position:absolute;inset:0;z-index:16;display:flex;flex-direction:column;align-items:center;justify-content:center;color:var(--text-secondary);background:var(--bg-page,#f2f5f7)}
.floor-unavailable strong{font-size:24px;color:var(--text-primary)}
.hospital-scene--unavailable-floor :deep(canvas),.hospital-scene--unavailable-floor :deep(.rmf-location-overlay){visibility:hidden}

.hospital-scene {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: transparent;
  transition: background-color 300ms ease;
}

.hospital-scene :deep(canvas) {
  display: block;
  width: 100%;
  height: 100%;
  cursor: default;
  outline: none;
  pointer-events: none;
}

.hospital-scene--interactive :deep(canvas) {
  cursor: grab;
  pointer-events: auto;
}

.hospital-scene--interactive :deep(canvas:active) {
  cursor: grabbing;
}

.hospital-scene--realtime {
  --map-page: var(--app-bg);
  --map-surface:var(--info-background);
  --map-surface-strong:var(--info-background);
  --map-primary: var(--theme-primary);
  --map-primary-hover: var(--theme-primary-hover);
  --map-primary-soft: var(--theme-primary-soft);
  --map-primary-dark: var(--theme-primary);
  --priority-high:var(--semantic-error);
  --priority-normal:var(--color-secondary);
  --priority-low:var(--color-neutral);
  --map-text:var(--text-primary);
  --map-muted:var(--text-secondary);
  --map-divider:var(--info-divider);
  border-radius: 6px;
}

.hospital-scene--realtime.hospital-scene--dark {
  --map-page:var(--app-background);
  --map-surface:var(--info-background);
  --map-surface-strong:var(--info-background);
  --map-primary:var(--theme-primary);
  --map-primary-hover:var(--theme-primary-hover);
  --map-primary-soft:var(--theme-primary-soft);
  --map-primary-dark:var(--theme-primary);
  --map-text:var(--text-primary);
  --map-muted:var(--text-secondary);
  --map-divider:var(--info-divider);
}

.hospital-scene--dark :global(.rmf-location){ color:var(--text-secondary); background:var(--info-background); border-color:var(--panel-border); box-shadow:var(--info-shadow); }
.hospital-scene--dark :global(.rmf-location strong) { color:var(--text-primary); }
.hospital-scene--dark :global(.rmf-location small) { color:var(--robot-color,var(--text-secondary)); }
.hospital-scene--dark :global(.rmf-location.is-active){ background:var(--info-background); border-color:color-mix(in srgb,var(--robot-color) 42%,transparent); }

.actor-graph-error { position: absolute; z-index: 24; top: 78px; left: 50%; display: grid; max-width: min(520px, calc(100% - 56px)); gap: 4px; padding: 12px 16px; color: var(--text-secondary); background: var(--panel-bg-strong); border: 1px solid rgba(199, 101, 91, 0.38); border-radius:var(--info-radius); box-shadow: var(--dropdown-shadow); font-size: 12.5px; transform: translateX(-50%); backdrop-filter:var(--info-backdrop); }
.actor-graph-error strong { color: #c7655b; font-size: 13.5px; }

.map-tool-rail{
  position: absolute;
  z-index: 18;
  top: 82px;
  left: 18px;
  display: grid;
  gap: 3px;
  padding: 5px;
  background:var(--info-background);
  border:var(--info-border);
  border-radius:var(--info-radius);
  box-shadow:var(--info-shadow);
  backdrop-filter: var(--info-backdrop);
  -webkit-backdrop-filter: var(--info-backdrop);
}

.map-tool-rail button { position:relative;display:grid; width:40px; height:40px; place-items:center; padding:0; color:var(--text-muted); background:transparent; border:0; border-radius:var(--radius-control); box-shadow:none; cursor:pointer; transition:color 160ms ease,background-color 160ms ease,box-shadow 160ms ease; }
.map-tool-rail button:hover { color:var(--theme-primary); background:var(--theme-primary-soft); }
.map-tool-rail button.is-active { color:var(--theme-primary); background:var(--theme-primary-soft); }
.map-tool-rail button:focus-visible { outline:none; background:var(--theme-primary-soft); box-shadow:0 0 0 3px var(--focus-ring); }
.map-tool-rail button::after{position:absolute;z-index:1000;top:50%;left:calc(100% + 8px);max-width:calc(100vw - 84px);padding:6px 8px;overflow:hidden;color:var(--text-primary);font-size:10.5px;line-height:1;white-space:nowrap;text-overflow:ellipsis;background:var(--dropdown-background);border:1px solid var(--panel-border);border-radius:var(--radius-small);box-shadow:var(--control-shadow);opacity:0;pointer-events:none;content:attr(aria-label);transform:translateY(-50%) translateX(-3px);transition:opacity 140ms ease,transform 140ms ease}.map-tool-rail button:hover::after,.map-tool-rail button:focus-visible::after{opacity:1;transform:translateY(-50%) translateX(0)}
.map-tool-rail__divider { display:none; }

.map-tool-drawer{ position:absolute; z-index:17; top:82px; left:66px; width:274px; max-height:calc(100% - 104px); overflow:auto; color:var(--map-muted); background:var(--info-background); border:var(--info-border); border-radius:6px; box-shadow:var(--info-shadow); backdrop-filter:var(--info-backdrop); -webkit-backdrop-filter:var(--info-backdrop); }
.map-tool-drawer--robots { width:260px; }
.map-tool-drawer header { display:flex; align-items:center; justify-content:space-between; min-height:40px; padding:0 10px 0 13px; border-bottom:1px solid var(--map-divider); }
.map-tool-drawer header strong { color:var(--map-text); font-size:16px; line-height:22px; font-weight:650; }
.map-tool-drawer--robots header strong { font-size:14px; }
.map-tool-drawer header button { display:grid; width:26px; height:26px; place-items:center; padding:0; color:var(--map-muted); background:transparent; border:0; border-radius:4px; cursor:pointer; }
.map-tool-drawer header button:hover { color:var(--map-primary-dark); background:var(--theme-primary-soft); }
.map-overview-summary,.map-robot-list,.map-task-list,.map-layer-list { display:grid; gap:6px; padding:10px; }
.map-overview-summary>div { display:flex; align-items:center; justify-content:space-between; min-height:36px; padding:0 5px; border-bottom:1px solid var(--map-divider); font-size:12px; }
.map-overview-summary strong { color:var(--map-text); }
.drawer-section-label { margin:4px 5px 1px; color:var(--map-muted); font-size:12px; line-height:16px; font-weight:600; }
.robot-segmented-filter { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:0; padding:0; overflow:hidden; background:color-mix(in srgb,var(--map-muted) 8%,#fff); border:0; border-radius:7px; }
.robot-segmented-filter button { display:grid; width:100%; min-height:32px; place-items:center; padding:3px 4px; color:var(--map-muted); background:transparent; border:0; border-radius:0; font-size:12px; font-weight:550; cursor:pointer; transition:background-color 160ms ease,color 160ms ease; }
.robot-segmented-filter button.is-active { color:var(--theme-primary); background:color-mix(in srgb,var(--theme-primary) 16%,#fff); box-shadow:none; }
.hospital-scene--dark .robot-segmented-filter { background:#303735; }
.hospital-scene--dark .robot-segmented-filter button.is-active { background:color-mix(in srgb,var(--theme-primary) 24%,#252c2b); }
.map-robot-list>.robot-list-row { display:grid; grid-template-columns:32px minmax(0,1fr) auto; align-items:center; min-height:46px; gap:8px; padding:5px 8px; color:var(--map-muted); text-align:left; background:transparent; border:0; border-radius:5px; cursor:pointer; transition:background-color 160ms ease; }
.map-robot-list>.robot-list-row:hover { color:var(--map-text); background:color-mix(in srgb,var(--robot-color) 6%,transparent); }
.map-robot-list>.robot-list-row.is-selected { color:var(--map-text); background:color-mix(in srgb,var(--robot-color) 14%,transparent); box-shadow:none; }
.robot-list-icon { display:grid; width:30px; height:30px; place-items:center; color:var(--robot-color); background:color-mix(in srgb,var(--robot-color) 10%,transparent); border:0; border-radius:4px; }
.robot-list-identity { display:grid; min-width:0; gap:1px; }
.robot-list-identity strong,.selected-robot-tasks h3 { overflow:hidden; color:var(--map-text); font-size:13px; line-height:17px; font-weight:600; text-overflow:ellipsis; white-space:nowrap; }
.robot-list-identity small { font-size:10.5px; line-height:14px; font-weight:500; }
.robot-list-battery { color:var(--map-text); font-size:12px; line-height:16px; font-weight:650; }
.robot-state-dot { width:6px; height:6px; background:var(--color-neutral); border-radius:50%; }
.robot-state-dot.is-busy { background:var(--map-primary); }.robot-state-dot.is-charging { background:var(--charging-station); }.robot-state-dot.is-idle { background:var(--color-neutral); }
.map-follow-toggle,.map-layer-list label { display:flex; align-items:center; min-height:31px; gap:8px; padding:0 5px; color:var(--map-muted); font-size:12px; cursor:pointer; }
.map-follow-toggle { margin-top:4px; padding-top:8px; border-top:1px solid var(--map-divider); }
.map-tool-drawer input { accent-color:var(--map-primary); }
.map-task-list .running-task-item { display:grid; grid-template-columns:minmax(0,1fr) auto; align-items:center; column-gap:10px; padding:9px 8px; background:var(--info-background); border-left:2px solid var(--robot-color); border-radius:4px; }
.running-task-copy{display:grid;min-width:0;gap:3px}.running-task-title{display:flex;min-width:0;gap:8px;align-items:baseline}.running-task-title>span,.running-task-copy small{flex:none;color:var(--map-muted);font-size:11px}.running-task-title strong{min-width:0;overflow:hidden;color:var(--map-text);font-size:12px;text-overflow:ellipsis;white-space:nowrap}.task-priority-badge{flex:none;padding:3px 7px;border-radius:5px;font-size:11px;font-weight:600;white-space:nowrap}.task-priority-badge.is-emergency,.task-priority-badge.is-high{color:var(--priority-high);background:color-mix(in srgb,var(--priority-high) 13%,transparent)}.task-priority-badge.is-normal{color:var(--priority-normal);background:color-mix(in srgb,var(--priority-normal) 14%,transparent)}.task-priority-badge.is-low{color:var(--priority-low);background:color-mix(in srgb,var(--priority-low) 14%,transparent)}
.simulation-mark{flex:none;color:var(--map-muted);font-size:10px;font-style:normal;font-weight:500}
.map-task-list p { margin:8px; font-size:12px; }
.alignment-debug-control { display:grid; gap:6px; margin-top:5px; padding:9px 5px 2px; border-top:1px solid var(--map-divider); }
.alignment-debug-control select { width:100%; padding:6px; color:var(--map-text); background:var(--map-surface-strong); border:1px solid var(--map-divider); border-radius:4px; }
.alignment-debug-control small { color:var(--map-muted); line-height:1.45; }
.priority-filter { display:grid; gap:2px; margin:7px 0 0; padding:10px 0 0; border:0; border-top:1px solid var(--map-divider); }
.priority-filter legend { padding:0 5px; }
.priority-isolate { margin-top:5px; padding-top:7px !important; border-top:1px solid var(--map-divider); }
.selected-robot-tasks { display:grid; gap:6px; margin-top:4px; padding-top:9px; border-top:1px solid var(--map-divider); }
.selected-robot-tasks h3 { margin:0 5px 2px; }
.robot-task-card { position:relative; display:grid; gap:3px; padding:9px 9px 9px 12px; overflow:hidden; color:var(--map-muted); background:var(--info-background); border-radius:5px; }
.robot-task-card::before { position:absolute; inset:0 auto 0 0; width:3px; background:var(--robot-color); content:''; }
.robot-task-card strong,.queued-task strong { color:var(--map-text); font-size:12px; line-height:17px; }
.robot-task-card span,.robot-task-card small,.queued-task small,.empty-task { font-size:11.5px; line-height:16px; }
.queued-task { display:flex; align-items:center; justify-content:space-between; min-height:36px; padding:7px 9px; color:var(--map-muted); text-align:left; background:var(--info-background); border:1px solid transparent; border-radius:4px; cursor:pointer; }
.queued-task:hover { border-color:var(--map-divider); }
.empty-task { margin:0 5px 4px; }
.robot-info-card { position:absolute; z-index:19; top:0; left:0; display:grid; box-sizing:border-box; width:220px; gap:10px; padding:13px; color:#fff; border-radius:var(--info-radius); pointer-events:auto; backdrop-filter:var(--info-backdrop); -webkit-backdrop-filter:var(--info-backdrop); }
.robot-info-card--selected{ background:var(--info-background); border:var(--info-border); box-shadow:var(--info-shadow); }
.robot-info-card--selected.is-following{box-shadow:var(--info-shadow);border-color:var(--theme-primary);}
.robot-info-card__header { display:flex; align-items:flex-start; justify-content:space-between; padding:0 0 9px; border-bottom:1px solid rgba(255,255,255,.27); }
.robot-info-card__header>div { display:grid; gap:2px; }
.robot-info-card__header strong { color:#fff; font-size:13px; line-height:17px; font-weight:720; letter-spacing:.035em; }
.robot-identity-chip { display:inline-block; width:8px; height:8px; margin-right:7px; background:var(--robot-color); border:1px solid rgba(255,255,255,.72); border-radius:50%; box-shadow:0 0 0 2px rgba(255,255,255,.16); }
.robot-info-card__header span { color:rgba(255,255,255,.78); font-size:10.5px; line-height:14px; }
.robot-info-card__header button { display:grid; width:24px; height:24px; place-items:center; padding:0; color:#fff; background:rgba(255,255,255,.13); border:1px solid rgba(255,255,255,.24); border-radius:6px; cursor:pointer; }
.robot-info-card__details { display:grid; gap:5px; margin:0; }
.robot-info-card__details>div { display:grid; grid-template-columns:42px minmax(0,1fr); align-items:baseline; gap:8px; }
.robot-info-card__details dt { color:rgba(255,255,255,.72); font-size:10.5px; line-height:15px; }
.robot-info-card__details dd { margin:0; overflow:hidden; color:#fff; font-size:11.5px; line-height:15px; font-weight:620; text-align:right; text-overflow:ellipsis; white-space:nowrap; }
.robot-info-card__actions { display:grid; grid-template-columns:1fr 1fr; gap:6px; }
.robot-info-card__actions button,.robot-camera-modes button { display:flex; align-items:center; justify-content:center; gap:4px; color:#fff; background:rgba(255,255,255,.14); border:1px solid rgba(255,255,255,.3); border-radius:6px; cursor:pointer; }
.robot-info-card__actions button { min-height:30px; padding:5px 8px; font-size:11px; font-weight:620; }
.robot-camera-modes { display:grid; grid-template-columns:repeat(3,1fr); gap:4px; padding:4px; background:rgba(255,255,255,.09); border:1px solid rgba(255,255,255,.16); border-radius:8px; }
.robot-camera-modes button { display:grid; min-height:38px; gap:1px; padding:3px 2px; border-color:transparent; font-size:9px; line-height:12px; }
.robot-camera-modes button.is-active { background:rgba(255,255,255,.25); border-color:rgba(255,255,255,.38); box-shadow:inset 0 1px 0 rgba(255,255,255,.25); }
.robot-mini-card{ width:170px; gap:7px; padding:10px 11px; color:var(--text-primary); background:color-mix(in srgb,var(--robot-color) 16%,var(--info-background)); border:0; border-radius:7px; box-shadow:0 5px 18px color-mix(in srgb,var(--robot-color) 16%,transparent); backdrop-filter:var(--info-backdrop); -webkit-backdrop-filter:var(--info-backdrop); }
.robot-mini-card.is-following{box-shadow:0 5px 18px color-mix(in srgb,var(--robot-color) 20%,transparent);}
.robot-mini-card .robot-info-card__header { align-items:center; padding:0 0 5px; border-color:rgba(43,42,39,.12); }
.robot-mini-card .robot-info-card__header strong { color:var(--text-primary); font-size:13px; letter-spacing:0; }
.robot-mini-card .robot-info-card__header button { width:21px; height:21px; color:var(--text-primary); background:rgba(255,255,255,.28); border-color:rgba(45,43,40,.14); border-radius:4px; }
.robot-mini-card>p { margin:0; color:var(--text-secondary); font-size:10.5px; font-weight:600; }
.robot-mini-card .robot-info-card__actions { display:block; }
.robot-mini-card .robot-info-card__actions button { width:100%; min-height:27px; color:var(--text-primary); background:rgba(255,255,255,.3); border-color:rgba(45,43,40,.15); border-radius:4px; }
.follow-camera-dock { position:fixed; z-index:1200; top:50%; right:22px; display:grid; justify-items:center; gap:6px; pointer-events:auto; transform:translateY(-50%); }
.follow-camera-trigger,.follow-camera-options button { display:grid; width:36px; height:36px; place-items:center; padding:0; color:var(--text-secondary); background:var(--info-background); border:1px solid rgba(102,108,105,.24); border-radius:50%; box-shadow:var(--info-shadow); cursor:pointer; }
.follow-camera-options { display:grid; position:absolute; right:0; bottom:44px; gap:6px; padding:5px; background:var(--info-background); border:1px solid rgba(102,108,105,.18); border-radius:var(--info-radius); box-shadow:var(--info-shadow); backdrop-filter:var(--info-backdrop); }
.follow-camera-options button { position:relative; width:32px; height:32px; }
.follow-camera-options button.is-active { color:var(--theme-primary); border-color:var(--theme-primary); box-shadow:inset 0 0 0 2px var(--theme-primary-soft); }
.follow-camera-options button::after { position:absolute; right:42px; padding:5px 7px; color:var(--text-primary); font-size:10px; white-space:nowrap; background:var(--dropdown-background); border:1px solid var(--glass-border); border-radius:5px; opacity:0; pointer-events:none; content:attr(aria-label); transform:translateX(3px); transition:opacity 140ms ease,transform 140ms ease; }
.follow-camera-options button:hover::after,.follow-camera-options button:focus-visible::after { opacity:1; transform:translateX(0); }
.follow-camera-trigger:hover,.follow-camera-options button:hover,.follow-camera-trigger:focus-visible,.follow-camera-options button:focus-visible { color:var(--theme-primary); border-color:currentColor; outline:none; }

:global(.rmf-location-overlay) { position: absolute; z-index: 14; inset: 0; overflow: hidden; pointer-events: none; }
:global(.rmf-location) { position:absolute; top:0; left:0; display:grid; min-width:132px; gap:1px; padding:9px 12px; color:var(--text-secondary); background:rgba(255,255,255,.76); background-image:none; border:1px solid rgba(84,88,86,.16); border-radius:5px; box-shadow:0 5px 14px rgba(35,40,38,.07); transform:translate(-50%,-100%); pointer-events:none; backdrop-filter:none; }
:global(.rmf-location::before) { position:absolute; top:0; bottom:0; left:0; width:3px; background:var(--location-color,var(--robot-color,var(--color-neutral))); border-radius:5px 0 0 5px; content:''; }
:global(.rmf-location::after) { position:absolute; top:100%; left:50%; width:1px; height:8px; content:''; background:var(--info-divider); }
:global(.rmf-location strong) { color:var(--text-primary); font-size:14px; font-weight:650; line-height:18px; white-space:nowrap; }
:global(.rmf-location small) { margin-top:3px; color:var(--robot-color,var(--color-neutral)); font-size:11.5px; line-height:15px; font-weight:600; white-space:nowrap; }
:global(.rmf-location:not(.is-active):not(.is-charging-station)){min-width:0;padding:5px 8px;box-shadow:none}
:global(.rmf-location:not(.is-active):not(.is-charging-station) strong){font-size:11px;font-weight:400;line-height:15px}
:global(.rmf-location.is-charging-station) { --location-color:var(--charging-station)!important; border-color:var(--charging-station-border); }
:global(.rmf-location.is-charging-station strong) { color:var(--charging-station); }
:global(.rmf-location.is-active) { background:rgba(255,255,255,.76); background-image:none; border-color:rgba(84,88,86,.16); box-shadow:0 5px 14px rgba(35,40,38,.07); }
:global(.rmf-location.is-approaching) { border-color:color-mix(in srgb,var(--robot-color) 42%,transparent); box-shadow:0 6px 16px color-mix(in srgb,var(--robot-glow) 18%,transparent); }
:global(.rmf-location.is-arrived) { border-color:var(--robot-color); box-shadow:0 7px 22px color-mix(in srgb,var(--robot-glow) 38%,transparent); }
:global(.rmf-location__success) { position:absolute; top:-7px; right:-7px; display:none; width:17px; height:17px; place-items:center; color:#fff; background:var(--success-color,var(--color-neutral)); border:2px solid rgba(255,255,255,.88); border-radius:50%; font-size:10px; line-height:1; box-shadow:0 3px 8px rgba(30,80,50,.18); }
:global(.rmf-location.is-completed .rmf-location__success) { display:grid; }
:global(.rmf-location.is-dimmed) { opacity:.38; }

/* White information surfaces retain series color only in compact markers. */
.robot-info-card,.robot-info-card__header strong,.robot-info-card__details dd{color:var(--text-primary)}
.robot-info-card__header span,.robot-info-card__details dt{color:var(--text-secondary)}
.robot-info-card__header{border-color:var(--info-divider)}
.robot-info-card__header button,.robot-info-card__actions button,.robot-camera-modes button{color:var(--text-secondary);background:transparent;border-color:var(--info-divider)}
.robot-info-card__header button:hover,.robot-info-card__actions button:hover,.robot-camera-modes button:hover,.queued-task:hover{color:var(--theme-primary);background:var(--theme-primary-soft)}
.robot-camera-modes button.is-active{color:var(--theme-primary);background:var(--theme-primary-soft);border-color:var(--theme-primary-border)}
:global(.rmf-location small){color:var(--text-primary);text-decoration:none}
:global(.rmf-location.is-approaching),:global(.rmf-location.is-arrived){box-shadow:var(--info-shadow)}
:global(.rmf-location.is-charging-station){border-color:var(--charging-station-border)}
:global(.rmf-location.is-charging-station::after){background:var(--charging-station)}
.hospital-scene--dark :global(.rmf-location.is-charging-station strong){color:var(--text-primary)}
:global(.rmf-room-overlay){position:absolute;z-index:12;inset:0;overflow:hidden;pointer-events:none}
:global(.rmf-room-label){position:absolute;top:0;left:0;padding:5px 8px;color:var(--map-text,var(--text-primary));font-size:11px;font-weight:400;line-height:15px;white-space:nowrap;background:color-mix(in srgb,var(--info-background) 78%,transparent);border:1px solid color-mix(in srgb,var(--text-secondary) 20%,transparent);border-radius:6px;box-shadow:0 3px 10px #0001;backdrop-filter:blur(5px)}
:global(.rmf-room-label::before){position:absolute;top:0;bottom:0;left:0;width:3px;background:var(--room-label-color,#DAC9A6);border-radius:5px 0 0 5px;content:''}
:global(.rmf-room-label[hidden]){display:none}
</style>

<style scoped>
.map-floor-picker{gap:0;padding:5px 0}
.map-tool-rail .floor-trigger{color:var(--theme-primary);font-size:15px}
.floor-options{position:absolute;z-index:21;top:4px;left:calc(100% + 9px);display:grid;gap:2px;width:62px;padding:4px;background:#fff;border:1px solid var(--map-divider);border-radius:8px;box-shadow:var(--info-shadow)}
.map-tool-rail .floor-option{width:100%;height:34px;color:var(--map-text);font-size:13px;border-radius:5px}
.map-tool-rail .floor-option[aria-checked="true"]{color:var(--theme-primary);background:#ffebe1}
.map-tool-rail .floor-option::after{display:none}
.hospital-scene--dark .floor-options{background:#303735}
.hospital-scene--dark .floor-option[aria-checked="true"]{background:#584036}
.map-running-tasks.map-tool-drawer{background:linear-gradient(145deg,rgba(255,253,235,.64),rgba(247,232,158,.44));border:1px solid rgba(221,185,69,.26);border-radius:16px;box-shadow:0 10px 30px #3d412910;backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px)}
.map-running-tasks header{margin:0 14px;padding:6px 0;border-bottom:1px solid #82744024}
.map-running-tasks .map-task-list{gap:0;padding:4px 14px 12px}
.map-running-tasks .running-task-item{display:block;padding:12px 0;background:transparent;border:0;border-bottom:1px solid #8274401a;border-radius:0}
.map-running-tasks .running-task-item:last-child{border-bottom:0}
.map-running-tasks .running-task-title strong{font-size:13px}
.robot-mini-card .robot-info-card__actions{display:grid;grid-template-columns:1fr;gap:6px}
.robot-mini-card .robot-info-card__actions .cancel-robot-task{color:#ad5149;background:#fff1ee90;border:0}
.robot-mini-card .robot-info-card__actions .cancel-robot-task:hover{color:#fff;background:#c95b50}
.hospital-scene--dark .map-running-tasks.map-tool-drawer{background:linear-gradient(145deg,#333a31bb,#49432699)}
</style>

<style scoped>
.live-map-data-notice{position:absolute;top:80px;right:20px;z-index:20;display:flex;align-items:center;gap:10px;max-width:calc(100% - 110px);padding:7px 10px;border-radius:7px;background:var(--info-background,#fff);color:var(--text-secondary);font-size:11px}.live-map-data-notice button{border:0;background:transparent;color:inherit;cursor:pointer}.unlocated-robot-list{padding:10px;border-top:1px solid var(--panel-border);font-size:11px;line-height:1.8;color:var(--text-secondary)}
</style>
