<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { SCENE_ASSETS } from '@/config/sceneAssets.js'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js'
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js'
import { OutlinePass } from 'three/addons/postprocessing/OutlinePass.js'
import { robotThermalZones, robotThermalSurface, robotBatteryZoneRules, thermalState, robotPresentation, stageLighting } from '@/config/robotHmi.js'
import { visualTokens } from '@/config/visualTokens.js'
import { primaryHotspots, robotComponents } from '@/config/robotComponentRules.js'
import { RobotStructureController } from '@/three/robot/RobotStructureController.js'
const props = defineProps({ robotId: String, temperature: { type: Number, default: null }, charging: Boolean, warning: Boolean })
const emit = defineEmits(['ready', 'entrance-complete', 'component-selected', 'interaction-change', 'component-hover'])
const hotspots = ref([]), labelsVisible = ref(false)
const host = ref(null), loading = ref(true), error = ref('')
let renderer, composer, scene, camera, controls, observer, model, frame, disposed = false
let renderPass, introOutline, hoverOutline, selectedOuterOutline, selectedInnerOutline
let presentationGroup, themeObserver, spotlight, rim, shadow, animateFrame
let isDark = false, outlinedSelection = null, selectionSweepStart = 0
let structure, interactionReady = false
const runtime = [], resources = new Set()
const reducedMotion = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
function resetView() {
  if (!controls) return
  if (structure && !interactionReady) return
  structure?.returnWhole(robotPresentation.camera)
  if (structure) return
  controls.reset()
  camera.position.set(...robotPresentation.camera)
  controls.target.set(0, .08, 0)
  controls.update()
}
function fitStage(immediate = false) {
  if(!structure || !host.value) return
  structure.setSafeRect({ left: .08, right: .92, top: .06, bottom: .94 }, immediate)
}
function projectHotspots() {
  if(!structure || !labelsVisible.value) {hotspots.value=[];return}
  camera.updateMatrixWorld();presentationGroup.updateMatrixWorld(true)
  const {width,height}=host.value.getBoundingClientRect(),safe=structure.safeRect
  const ids=primaryHotspots.includes(structure.selected) || !structure.selected ? primaryHotspots : [...primaryHotspots.slice(0,4),structure.selected]
  const points=ids.map(id=>{
    const record=structure.records.find(r=>r.id===id)
    const p=new THREE.Box3().setFromObject(record.mesh).getCenter(new THREE.Vector3()).project(camera)
    return {id,label:robotComponents.find(c=>c.id===id).label,index:String(robotComponents.findIndex(c=>c.id===id)+1).padStart(2,'0'),x:(p.x+1)*width/2,y:(1-p.y)*height/2,z:p.z}
  }).filter(p=>p.z>-1&&p.z<1).sort((a,b)=>a.y-b.y)
  const labelWidth = width < 400 ? 100 : 140
  const left=4,right=width-labelWidth-4
  const used=[0,0]
  points.forEach((p,i)=>{
    const side=i%2;p.lx=side?right:left
    p.ly=Math.min(safe.bottom*height-28,Math.max(safe.top*height,p.y-14,used[side]+36))
    used[side]=p.ly
  })
  hotspots.value=points
}
function hoverPart(id) {if(!interactionReady)return;structure.hovered=id;emit('component-hover',id)}
function updateOutlines(time) {
  if (!structure || !introOutline) return
  const records = structure.records
  introOutline.selectedObjects = []
  const selected = records.filter(record => record.id === structure.selected).map(record => record.mesh)
  const hovered = structure.hovered && structure.hovered !== structure.selected ? records.filter(record => record.id === structure.hovered).map(record => record.mesh) : []
  if (outlinedSelection !== structure.selected) { outlinedSelection = structure.selected; selectionSweepStart = time }
  const selectionAge = time - selectionSweepStart
  const sweep = selected.length && selectionAge < 520 ? Math.sin(Math.PI * selectionAge / 520) : 0
  const selectedIsWarning = props.warning && selected.some(mesh => robotThermalZones.chassis.includes(mesh.name))
  const selectedColor = selectedIsWarning ? visualTokens.error : visualTokens.primary
  const glowColor = visualTokens.primary
  introOutline.visibleEdgeColor.set(visualTokens.primary)
  introOutline.hiddenEdgeColor.set(visualTokens.primary)
  hoverOutline.visibleEdgeColor.set(visualTokens.primary)
  hoverOutline.hiddenEdgeColor.set(visualTokens.primary)
  selectedOuterOutline.visibleEdgeColor.set(glowColor)
  selectedOuterOutline.hiddenEdgeColor.set(glowColor)
  selectedInnerOutline.visibleEdgeColor.set(selectedColor)
  selectedInnerOutline.hiddenEdgeColor.set(selectedColor)
  hoverOutline.selectedObjects = hovered
  selectedOuterOutline.selectedObjects = selected
  selectedInnerOutline.selectedObjects = selected
  selectedOuterOutline.edgeStrength = 2.2 + sweep * 1.6
  selectedInnerOutline.edgeStrength = 3.2 + sweep * 2
}
function updateMaterials(time = 0) {
  const critical = props.warning && thermalState(props.temperature) === 'critical'
  const pulse = reducedMotion() ? .6 : .55 + .2 * Math.sin(time / 900)
  runtime.forEach(({ mesh, material, original, heat }) => {
    const heatColor = props.temperature >= 70 ? '#C96561' : props.temperature >= 55 ? '#C96F3B' : props.temperature >= 35 ? '#D5AD4E' : '#A9CFC4'
    heat.enabled.value = critical && Number.isFinite(props.temperature) ? 1 : 0
    heat.color.value.set(heatColor)
    heat.intensity.value = critical ? pulse : .12
    material.color.copy(original.color)
    material.emissive?.copy(original.emissive || new THREE.Color(0))
    material.emissiveIntensity = original.emissiveIntensity ?? 1
    const zone = robotThermalZones.chassis.includes(mesh.name)
    if (zone && critical && Number.isFinite(props.temperature)) {
      const color = props.temperature >= 70 ? '#C96561' : props.temperature >= 55 ? '#C96F3B' : props.temperature >= 35 ? '#D5AD4E' : '#A9CFC4'
      material.color.set(color)
      material.emissive?.set(color)
      material.emissiveIntensity = critical ? pulse : .18
    }
    if (props.charging && robotBatteryZoneRules.includes(mesh.name)) {
      material.emissive?.set('#4F9F91')
      material.emissiveIntensity = pulse
    }
    structure?.styleMaterial(mesh, material, original)
  })
}
function trackModel(root) {
  root.traverse((mesh) => {
    if (!mesh.isMesh) return
    resources.add(mesh.geometry)
    const source = Array.isArray(mesh.material) ? mesh.material : [mesh.material]
    const cloned = source.map((original) => {
      resources.add(original)
      Object.values(original).forEach((value) => { if (value?.isTexture) resources.add(value) })
      const material = original.clone()
      resources.add(material)
      const heat = { enabled: { value: 0 }, color: { value: new THREE.Color() }, intensity: { value: 0 } }
      if (mesh.name === robotThermalSurface.object) {
        material.onBeforeCompile = (shader) => {
          shader.uniforms.hmiHeatEnabled = heat.enabled
          shader.uniforms.hmiHeatColor = heat.color
          shader.uniforms.hmiHeatIntensity = heat.intensity
          shader.vertexShader = 'varying float hmiLocalHeight;\n' + shader.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\nhmiLocalHeight = position.y;')
          shader.fragmentShader = 'varying float hmiLocalHeight;\nuniform float hmiHeatEnabled;\nuniform vec3 hmiHeatColor;\nuniform float hmiHeatIntensity;\n' + shader.fragmentShader
            .replace('#include <color_fragment>', `#include <color_fragment>\nfloat hmiHeatMask = (1.0 - smoothstep(${robotThermalSurface.maxLocalHeight - 2}.0, ${robotThermalSurface.maxLocalHeight}.0, hmiLocalHeight)) * hmiHeatEnabled;\ndiffuseColor.rgb = mix(diffuseColor.rgb, hmiHeatColor, hmiHeatMask * 0.65);`)
            .replace('#include <emissivemap_fragment>', '#include <emissivemap_fragment>\ntotalEmissiveRadiance += hmiHeatColor * hmiHeatMask * hmiHeatIntensity;')
        }
        material.customProgramCacheKey = () => 'hmi-chassis-thermal-v1'
      }
      runtime.push({ mesh, material, original, heat })
      return material
    })
    mesh.material = Array.isArray(mesh.material) ? cloned : cloned[0]
  })
}
function showWholeRobot() {
  if (!structure || !presentationGroup || !animateFrame || disposed) return
  cancelAnimationFrame(frame)
  structure.reset()
  presentationGroup.rotation.y = 0
  structure.applyExplosion(0)
  fitStage(true)
  renderer.domElement.style.opacity = '1'
  shadow.material.opacity = shadow.userData.opacity
  spotlight.intensity = spotlight.userData.targetIntensity
  labelsVisible.value = true
  interactionReady = true
  emit('interaction-change', true)
  emit('entrance-complete')
  frame = requestAnimationFrame(animateFrame)
}
onMounted(async () => {
  try {
    renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
    renderer.setClearColor(0, 0)
    renderer.outputColorSpace = THREE.SRGBColorSpace
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1.15
    host.value.prepend(renderer.domElement)
    scene = new THREE.Scene()
    camera = new THREE.PerspectiveCamera(robotPresentation.fov, 1, .01, 100)
    composer = new EffectComposer(renderer)
    renderPass = new RenderPass(scene, camera)
    const outlineResolution = new THREE.Vector2(1, 1)
    introOutline = new OutlinePass(outlineResolution, scene, camera)
    hoverOutline = new OutlinePass(outlineResolution, scene, camera)
    selectedOuterOutline = new OutlinePass(outlineResolution, scene, camera)
    selectedInnerOutline = new OutlinePass(outlineResolution, scene, camera)
    introOutline.edgeStrength = 1.8; introOutline.edgeThickness = 1; introOutline.edgeGlow = .05
    hoverOutline.edgeStrength = 1.2; hoverOutline.edgeThickness = 1; hoverOutline.edgeGlow = 0
    selectedOuterOutline.edgeStrength = 2.2; selectedOuterOutline.edgeThickness = 2.2; selectedOuterOutline.edgeGlow = .08
    selectedInnerOutline.edgeStrength = 3.2; selectedInnerOutline.edgeThickness = .7; selectedInnerOutline.edgeGlow = 0
    ;[renderPass, introOutline, hoverOutline, selectedOuterOutline, selectedInnerOutline].forEach(pass => composer.addPass(pass))
    controls = new OrbitControls(camera, renderer.domElement)
    controls.enablePan = false
    controls.enableDamping = true
    controls.dampingFactor = .06
    controls.minDistance = 3.8
    controls.maxDistance = 9
    controls.minPolarAngle = .35
    controls.maxPolarAngle = Math.PI * .72
    resetView()
    controls.saveState()
    controls.enabled = false
    scene.add(new THREE.HemisphereLight(0xfff3df, 0x626963, 1.6))
    spotlight = new THREE.SpotLight(0xfff3df, 38, 18, Math.PI / 5, .85, 1.5)
    spotlight.position.set(0, 6, 2)
    spotlight.target.position.set(0, -.8, 0)
    scene.add(spotlight, spotlight.target)
    const key = new THREE.DirectionalLight(0xfff3df, 1.6)
    key.position.set(3, 3, 5); scene.add(key)
    rim = new THREE.DirectionalLight(0xf2c6a4, 1.8)
    rim.position.set(-3, 2, -3); scene.add(rim)
    const updateLighting = () => {
      isDark = host.value?.closest('[data-theme]')?.getAttribute('data-theme') === 'dark' || document.documentElement.dataset.theme === 'dark'
      const theme = stageLighting[isDark ? 'dark' : 'light']
      spotlight.color.set(theme.spotlight)
      spotlight.userData.targetIntensity = theme.intensity
      rim.color.set(theme.rim)
      if (shadow) shadow.userData.opacity = isDark ? .19 : .12
    }
    updateLighting()
    themeObserver = new MutationObserver(updateLighting)
    themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'], subtree: true })
    const shadowCanvas = document.createElement('canvas')
    shadowCanvas.width = shadowCanvas.height = 128
    const context = shadowCanvas.getContext('2d')
    const gradient = context.createRadialGradient(64, 64, 4, 64, 64, 64)
    gradient.addColorStop(0, 'rgba(32,24,18,1)')
    gradient.addColorStop(.3, 'rgba(32,24,18,.35)')
    gradient.addColorStop(.65, 'rgba(32,24,18,.04)')
    gradient.addColorStop(1, 'rgba(32,24,18,0)')
    context.fillStyle = gradient; context.fillRect(0, 0, 128, 128)
    const texture = new THREE.CanvasTexture(shadowCanvas)
    const shadowMaterial = new THREE.MeshBasicMaterial({ map: texture, transparent: true, depthWrite: false })
    const shadowGeometry = new THREE.PlaneGeometry(2.4, 2.4)
    shadow = new THREE.Mesh(shadowGeometry, shadowMaterial)
    shadow.rotation.x = -Math.PI / 2
    shadow.position.y = -1.405
    scene.add(shadow)
    updateLighting()
    ;[texture, shadowMaterial, shadowGeometry].forEach(resource => resources.add(resource))
    observer = new ResizeObserver(() => {
      if (!host.value || disposed) return
      const { width, height } = host.value.getBoundingClientRect()
      renderer.setSize(Math.max(width, 1), Math.max(height, 1))
      composer.setSize(Math.max(width, 1), Math.max(height, 1))
      camera.aspect = width / Math.max(height, 1)
      camera.updateProjectionMatrix()
      fitStage(true)
    })
    observer.observe(host.value)
    const gltf = await new GLTFLoader().loadAsync(SCENE_ASSETS.robot)
    model = gltf.scene
    trackModel(model)
    if (disposed) { resources.forEach((resource) => resource.dispose()); resources.clear(); return }
    console.table(runtime.map(({ mesh, original }) => ({ object: mesh.name, parent: mesh.parent?.name, material: original.name })))
    const box = new THREE.Box3().setFromObject(model)
    const size = box.getSize(new THREE.Vector3()), center = box.getCenter(new THREE.Vector3())
    const scale = robotPresentation.modelHeight / size.y
    const normalizationGroup = new THREE.Group()
    normalizationGroup.add(model)
    normalizationGroup.scale.setScalar(scale)
    normalizationGroup.position.copy(center).multiplyScalar(-scale)
    presentationGroup = new THREE.Group()
    presentationGroup.add(normalizationGroup)
    scene.add(presentationGroup)
    structure = new RobotStructureController({ root:presentationGroup, camera, controls, canvas:renderer.domElement,
      onSelect:id => emit('component-selected', id), canInteract:() => interactionReady, reducedMotion })
    fitStage(true)
    loading.value = false
    emit('ready')
    animateFrame = (time) => {
      if (disposed) return
      frame = requestAnimationFrame(animateFrame)
      if (document.hidden) return
      structure.update(time)
      controls.enabled = interactionReady && !structure.focusTween && !structure.explodeTween
      if (controls.enabled) controls.update()
      updateMaterials(time)
      updateOutlines(time)
      projectHotspots()
      composer.render()
    }
    showWholeRobot()
  } catch (reason) {
    if (!disposed) { error.value = '3D 模型無法載入，請確認瀏覽器支援 WebGL 後重新整理。'; loading.value = false; emit('ready'); console.error(reason) }
  }
})
watch(() => props.robotId, showWholeRobot)
defineExpose({ resetView, selectComponent: id => structure?.select(id), setStructureMode: mode => structure?.setMode(mode) })
onBeforeUnmount(() => {
  disposed = true
  cancelAnimationFrame(frame)
  observer?.disconnect()
  themeObserver?.disconnect()
  structure?.dispose()
  controls?.dispose()
  resources.forEach((resource) => resource.dispose())
  resources.clear()
  ;[introOutline, hoverOutline, selectedOuterOutline, selectedInnerOutline, renderPass].forEach(pass => pass?.dispose?.())
  composer?.dispose()
  renderer?.dispose()
  renderer?.domElement.remove()
})
</script>
<template>
  <div ref="host" class="robot-viewport" @dblclick="resetView">
    <div class="robot-part-callouts" :class="{ 'is-ready': interactionReady }" aria-label="結構標註">
      <svg aria-hidden="true"><g v-for="part in hotspots" :key="part.id" :class="{ 'is-selected': structure?.selected === part.id }"><line class="robot-part-connector" :x1="part.x" :y1="part.y" :x2="part.lx < part.x ? part.lx + (host?.clientWidth < 400 ? 100 : 140) : part.lx" :y2="part.ly+14"/><circle :cx="part.x" :cy="part.y" r="2.5"/></g></svg>
      <button v-for="part in hotspots" :key="part.id" class="robot-part-hotspot" :class="{ 'is-selected': structure?.selected === part.id }" :disabled="!interactionReady" :style="{left:part.lx+'px',top:part.ly+'px'}" @pointerenter="hoverPart(part.id)" @pointerleave="hoverPart(null)" @focus="hoverPart(part.id)" @blur="hoverPart(null)" @click="structure?.select(part.id)"><small>{{ part.index }}</small>{{ part.label }}</button>
    </div>
    <div v-if="loading" class="viewport-message" role="status"><span class="loading-orbit"></span>正在載入機器人</div>
    <div v-if="error" class="viewport-message" role="alert">{{ error }}</div>
  </div>
</template>
<style scoped>
.robot-viewport{position:relative;width:100%;height:100%;min-height:0;touch-action:none}.robot-viewport :deep(canvas){display:block;width:100%;height:100%;cursor:grab}.robot-viewport :deep(canvas:active){cursor:grabbing}.viewport-message{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;flex-direction:column;gap:16px;color:var(--text-muted);font-size:12px;text-align:center}.loading-orbit{width:46px;height:46px;border:2px solid var(--panel-border);border-top-color:var(--theme-primary);border-radius:50%;animation:load 1.2s linear infinite}@keyframes load{to{transform:rotate(360deg)}}@media(prefers-reduced-motion:reduce){.loading-orbit{animation:none}}
</style>
