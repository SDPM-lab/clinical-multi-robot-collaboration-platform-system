import * as THREE from 'three'
import { createGltfLoader, runtimeModelUrl } from '@/three/loaders/createGltfLoader.js'
import { clone as cloneSkeleton } from 'three/examples/jsm/utils/SkeletonUtils.js'
import { BAYMAX_MODEL_URL, baymaxConfig } from '@/config/baymaxNurseConfig.js'

const WAYPOINT_EPSILON = 0.025
const NURSE_SKIN_MATERIAL = 'White'
const NURSE_SKIN_COLOR = 0xf1c8d0

const clipSummary = (clip) => ({
  name: clip.name,
  duration: clip.duration,
  tracks: clip.tracks.length,
})

const findClip = (clips, actionName) => (
  clips.find((clip) => clip.name === actionName)
  || clips.find((clip) => clip.name.toLowerCase().includes(actionName.toLowerCase()))
  || null
)

const makeInPlaceClip = (clip) => {
  const inPlace = clip.clone()
  inPlace.name = `${clip.name}_InPlace`
  inPlace.tracks.forEach((track) => {
    if (!/\.position$/i.test(track.name) || !/(?:^|\.)Root\.position$/i.test(track.name)) return
    const itemSize = track.getValueSize()
    if (itemSize < 3 || track.values.length < 3) return
    const fixedX = track.values[0]
    const fixedZ = track.values[2]
    for (let index = 0; index < track.values.length; index += itemSize) {
      track.values[index] = fixedX
      track.values[index + 2] = fixedZ
    }
  })
  return inPlace
}

const disposeModelResources = (model) => {
  const geometries = new Set()
  const materials = new Set()
  const textures = new Set()

  model?.traverse((object) => {
    if (object.geometry) geometries.add(object.geometry)
    const objectMaterials = Array.isArray(object.material)
      ? object.material
      : [object.material]
    objectMaterials.filter(Boolean).forEach((material) => {
      materials.add(material)
      Object.values(material).forEach((value) => {
        if (value?.isTexture) textures.add(value)
      })
    })
  })

  textures.forEach((texture) => texture.dispose())
  materials.forEach((material) => material.dispose())
  geometries.forEach((geometry) => geometry.dispose())
}

export class BaymaxNurseController {
  constructor({
    actorGroup,
    config = baymaxConfig,
    loader = createGltfLoader(),
    animationOffset = 0,
    name = 'Baymax Nurse',
  }) {
    if (!actorGroup) throw new Error('BaymaxNurseController requires an actorGroup.')

    this.config = { ...baymaxConfig, ...config }
    this.actorMotionWrapper = actorGroup
    this.actorMotionWrapper.name = `${name} ActorMotionWrapper`
    // Compatibility for the Graph coordinator: all world motion belongs here.
    this.actorGroup = this.actorMotionWrapper
    this.actorModelWrapper = new THREE.Group()
    this.actorModelWrapper.name = `${name} ActorModelWrapper`
    this.actorModelWrapper.rotation.y = this.config.forwardAxisOffset
    this.actorMotionWrapper.add(this.actorModelWrapper)
    this.forwardArrow = null
    const axisDebugEnabled = import.meta.env.DEV
      && new URLSearchParams(window.location.search).get('actorAxisDebug') === '1'
    if (axisDebugEnabled) {
      this.forwardArrow = new THREE.ArrowHelper(
        new THREE.Vector3(0, 0, 1),
        new THREE.Vector3(0, 0.05, 0),
        0.8,
        0xff0000,
        0.18,
        0.1,
      )
      this.forwardArrow.name = `${name} Forward Axis Debug Arrow`
      this.actorMotionWrapper.add(this.forwardArrow)
    }
    this.loader = loader
    this.animationOffset = animationOffset
    this.name = name
    this.model = null
    this.mixer = null
    this.walkAction = null
    this.idleAction = null
    this.path = []
    this.waypointIndex = 0
    this.visible = true
    this.disposed = false
    this.activeAction = null
    this.originalBounds = null
    this.scaledBounds = null
    this.finalScale = 1
    this.baseScale = 1
    this.direction = new THREE.Vector3()
    this.targetQuaternion = new THREE.Quaternion()
  }

  async load() {
    const gltf = await this.loader.loadAsync(runtimeModelUrl(BAYMAX_MODEL_URL))

    console.table(gltf.animations.map(clipSummary))

    if (this.disposed) {
      disposeModelResources(gltf.scene)
      return null
    }

    const baymaxMeshes = []
    gltf.scene.traverse((object) => {
      if (!object.isMesh) return
      const materials = Array.isArray(object.material) ? object.material : [object.material]
      materials.forEach((material) => baymaxMeshes.push({
        object: object.name,
        material: material?.name || '(unnamed material)',
      }))
    })
    console.table(baymaxMeshes)

    this.model = cloneSkeleton(gltf.scene)
    this.model.name = this.name
    this.model.traverse((object) => {
      if (!object.isMesh || !object.material) return
      const materials = Array.isArray(object.material) ? object.material : [object.material]
      const updated = materials.map((material) => {
        if (material?.name !== NURSE_SKIN_MATERIAL) return material
        const pinkMaterial = material.clone()
        pinkMaterial.name = `${material.name}_NurseSkinPink`
        pinkMaterial.color.setHex(NURSE_SKIN_COLOR)
        pinkMaterial.roughness = 0.72
        pinkMaterial.metalness = 0
        pinkMaterial.needsUpdate = true
        return pinkMaterial
      })
      object.material = Array.isArray(object.material) ? updated : updated[0]
    })
    this.model.updateMatrixWorld(true)

    this.originalBounds = new THREE.Box3().setFromObject(this.model)
    if (this.originalBounds.isEmpty()) {
      throw new Error('baymax_nurse.glb does not contain visible geometry.')
    }

    const originalSize = this.originalBounds.getSize(new THREE.Vector3())
    if (originalSize.y <= 0) throw new Error('baymax_nurse.glb has an invalid height.')

    this.baseScale = this.config.targetHeight / originalSize.y
    this.finalScale = this.baseScale * this.config.displayScaleMultiplier
    this.model.scale.setScalar(this.finalScale)
    this.model.updateMatrixWorld(true)

    const scaledBounds = new THREE.Box3().setFromObject(this.model)
    const scaledCenter = scaledBounds.getCenter(new THREE.Vector3())
    this.model.position.x -= scaledCenter.x
    this.model.position.y -= scaledBounds.min.y
    this.model.position.z -= scaledCenter.z
    this.model.updateMatrixWorld(true)
    this.scaledBounds = new THREE.Box3().setFromObject(this.model)

    this.model.traverse((object) => {
      if (!object.isMesh) return
      object.castShadow = true
      object.receiveShadow = true
    })

    const rigNames = []
    this.model.traverse((object) => {
      if (object.isBone || /armature|rig/i.test(object.name)) rigNames.push(object.name)
    })

    console.info('baymax_nurse.glb rig names:', [...new Set(rigNames)].filter(Boolean))
    console.info('baymax_nurse.glb original bounding box:', {
      min: this.originalBounds.min.toArray(),
      max: this.originalBounds.max.toArray(),
      size: originalSize.toArray(),
    })
    console.info('baymax_nurse.glb normalized actor:', {
      baseScale: this.baseScale,
      displayScaleMultiplier: this.config.displayScaleMultiplier,
      finalScale: this.finalScale,
      height: this.scaledBounds.getSize(new THREE.Vector3()).y,
      floorY: this.config.floorY,
      nativeForwardAxis: '+X',
      forwardAxisOffset: this.config.forwardAxisOffset,
      wrapperHierarchy: `${this.actorMotionWrapper.name} > ${this.actorModelWrapper.name}`,
    })

    this.actorModelWrapper.add(this.model)
    this.actorMotionWrapper.position.y = this.config.floorY
    this.actorMotionWrapper.visible = this.visible

    if (gltf.animations.length > 0) {
      this.mixer = new THREE.AnimationMixer(this.model)
      const walkClip = findClip(gltf.animations, 'Walk')
      const idleClip = findClip(gltf.animations, 'Idle')

      if (walkClip) {
        const inPlaceWalkClip = makeInPlaceClip(walkClip)
        this.walkAction = this.mixer.clipAction(inPlaceWalkClip)
        this.walkAction.setLoop(THREE.LoopRepeat, Infinity)
        this.walkAction.play()
        this.walkAction.time = this.animationOffset % inPlaceWalkClip.duration
        this.activeAction = this.walkAction
        console.info(`Baymax walk clip selected: ${walkClip.name}; planar root motion locked for lane accuracy.`)
      } else {
        console.warn('baymax_nurse.glb has animation clips, but no Walk animation was found.')
      }

      if (idleClip) {
        this.idleAction = this.mixer.clipAction(idleClip)
        this.idleAction.setLoop(THREE.LoopRepeat, Infinity)
      } else {
        console.warn('baymax_nurse.glb has no Idle clip; stationary nurses keep the exported standing pose.')
      }
    } else {
      console.warn('baymax_nurse.glb 目前只有骨架，沒有可播放的 Walk 動畫。')
    }

    this.syncAction(Boolean(this.walkAction && this.path.length > 1 && this.visible))
    return this.model
  }

  update(delta) {
    const safeDelta = Math.max(0, Number(delta) || 0)
    this.mixer?.update(safeDelta)

    const moving = this.visible && this.path.length > 1 && safeDelta > 0
    this.syncAction(Boolean(moving && this.walkAction))
    if (!moving) return

    let remainingDistance = this.config.speed * safeDelta
    let facingDirection = null
    let consecutiveReachedPoints = 0

    while (remainingDistance > 0) {
      const target = this.path[this.waypointIndex]
      this.direction.copy(target).sub(this.actorGroup.position)
      this.direction.y = 0
      const distanceToTarget = this.direction.length()

      if (distanceToTarget <= WAYPOINT_EPSILON) {
        this.actorGroup.position.x = target.x
        this.actorGroup.position.z = target.z
        this.waypointIndex = (this.waypointIndex + 1) % this.path.length
        consecutiveReachedPoints += 1
        if (consecutiveReachedPoints >= this.path.length) break
        continue
      }

      consecutiveReachedPoints = 0
      this.direction.normalize()
      facingDirection = this.direction
      const step = Math.min(remainingDistance, distanceToTarget)
      this.actorGroup.position.addScaledVector(this.direction, step)
      this.actorGroup.position.y = this.config.floorY
      remainingDistance -= step

      if (step < distanceToTarget) break
      this.waypointIndex = (this.waypointIndex + 1) % this.path.length
    }

    if (facingDirection) {
      const yaw = Math.atan2(facingDirection.x, facingDirection.z)
      this.targetQuaternion.setFromAxisAngle(THREE.Object3D.DEFAULT_UP, yaw)
      const rotationAlpha = 1 - Math.exp(-this.config.turnSpeed * safeDelta)
      this.actorMotionWrapper.quaternion.slerp(this.targetQuaternion, rotationAlpha)
    }
  }

  updateGraphMotion(delta, target = null, speed = 0) {
    const safeDelta = Math.max(0, Number(delta) || 0)
    this.mixer?.update(safeDelta)
    if (!target || !this.visible || safeDelta <= 0) {
      this.syncAction(false)
      return false
    }

    this.direction.copy(target).sub(this.actorGroup.position)
    this.direction.y = 0
    const distanceToTarget = this.direction.length()
    if (distanceToTarget <= WAYPOINT_EPSILON) {
      this.actorGroup.position.set(target.x, this.config.floorY, target.z)
      this.syncAction(false)
      return true
    }

    this.direction.normalize()
    const step = Math.min(distanceToTarget, Math.max(0, speed) * safeDelta)
    this.actorGroup.position.addScaledVector(this.direction, step)
    this.actorGroup.position.y = this.config.floorY
    const yaw = Math.atan2(this.direction.x, this.direction.z)
    this.targetQuaternion.setFromAxisAngle(THREE.Object3D.DEFAULT_UP, yaw)
    this.actorMotionWrapper.quaternion.slerp(
      this.targetQuaternion,
      1 - Math.exp(-this.config.turnSpeed * safeDelta),
    )
    this.syncAction(Boolean(this.walkAction))
    return distanceToTarget - step <= WAYPOINT_EPSILON
  }

  setPath(points) {
    this.path = (points || []).map(([x, , z]) => (
      new THREE.Vector3(Number(x), this.config.floorY, Number(z))
    ))
    this.waypointIndex = this.path.length > 1 ? 1 : 0
    if (this.path.length > 0) this.setPosition(this.path[0])
    this.syncAction(Boolean(this.walkAction && this.path.length > 1 && this.visible))
  }

  setVisible(visible) {
    this.visible = Boolean(visible)
    this.actorMotionWrapper.visible = this.visible
    this.syncAction(Boolean(this.walkAction && this.path.length > 1 && this.visible))
  }

  setPosition(position) {
    const source = position?.isVector3
      ? position
      : new THREE.Vector3(...position)
    this.actorGroup.position.set(source.x, this.config.floorY, source.z)
  }

  syncAction(shouldWalk) {
    if (this.walkAction && !this.idleAction) {
      this.walkAction.paused = !shouldWalk
      if (shouldWalk && !this.walkAction.isRunning()) this.walkAction.play()
      return
    }
    const nextAction = shouldWalk ? this.walkAction : this.idleAction
    if (!nextAction || nextAction === this.activeAction) return

    nextAction.reset().play()
    const duration = nextAction.getClip().duration
    nextAction.time = duration > 0 ? this.animationOffset % duration : 0
    if (this.activeAction) this.activeAction.crossFadeTo(nextAction, 0.25, false)
    this.activeAction = nextAction
  }

  dispose() {
    this.disposed = true
    this.walkAction?.stop()
    this.idleAction?.stop()
    this.mixer?.stopAllAction()
    if (this.mixer && this.model) this.mixer.uncacheRoot(this.model)
    if (this.model) {
      this.actorModelWrapper.remove(this.model)
      disposeModelResources(this.model)
    }

    this.model = null
    this.mixer = null
    this.walkAction = null
    this.idleAction = null
    this.activeAction = null
    this.path = []
    this.forwardArrow?.line?.geometry?.dispose()
    this.forwardArrow?.line?.material?.dispose()
    this.forwardArrow?.cone?.geometry?.dispose()
    this.forwardArrow?.cone?.material?.dispose()
    this.forwardArrow?.removeFromParent()
    this.actorModelWrapper.removeFromParent()
    this.forwardArrow = null
  }
}
