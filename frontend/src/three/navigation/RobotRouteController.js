import * as THREE from 'three'
import { clone as cloneSkeleton } from 'three/examples/jsm/utils/SkeletonUtils.js'
import { DEFAULT_ROBOT_ASSET, loadRobotAsset } from '@/three/robot/robotModelAssets.js'
import { poseAgibotMapArms } from '@/three/robot/poseAgibotMapArms.js'

export const REALTIME_ROBOT_SCALE_MULTIPLIER = 1.4
export const ROBOT_HIT_TARGET = Object.freeze({ radius: 0.45, height: 0.8, segments: 16 })
// Robot Status views the AGIBOT face from roughly +X; align that direction with map route forward (+Z).
const AGIBOT_ROUTE_YAW = -Math.atan2(1, 0.28)

const samplePolyline = (points, distance) => {
  if (points.length < 2) return { point: points[0]?.clone(), tangent: new THREE.Vector3(0, 0, 1), total: 0 }
  const lengths = points.slice(1).map((point, index) => point.distanceTo(points[index]))
  const total = lengths.reduce((sum, length) => sum + length, 0)
  let remaining = THREE.MathUtils.clamp(distance, 0, total)
  for (let index = 0; index < lengths.length; index += 1) {
    const tangent = points[index + 1].clone().sub(points[index]).normalize()
    if (remaining <= lengths[index]) return { point: points[index].clone().addScaledVector(tangent, remaining), tangent, total }
    remaining -= lengths[index]
  }
  return { point: points.at(-1).clone(), tangent: points.at(-1).clone().sub(points.at(-2)).normalize(), total }
}

export class RobotRouteController {
  constructor({ id, parent, points = [], progress = 0, color, floorY = 0, targetHeight = 0.72, offline = false, modelAssetKey = DEFAULT_ROBOT_ASSET }) {
    this.id = id
    this.wrapper = new THREE.Group()
    this.wrapper.name = `Robot ${id.slice(1)} Wrapper`
    parent.add(this.wrapper)
    this.points = points
    this.progress = progress
    this.color = new THREE.Color(color)
    this.floorY = floorY
    this.targetHeight = targetHeight
    this.speed = 0.42
    this.distance = 0
    this.totalDistance = 0
    this.model = null
    this.hitTarget = null
    this.baseRobotScale = new THREE.Vector3(1, 1, 1)
    this.mixer = null
    this.selected = false
    this.following = false
    this.offline = offline
    this.modelAssetKey = modelAssetKey
    this.emphasis = 1
    this.boundsHeight = targetHeight
    this.targetQuaternion = new THREE.Quaternion()
    this.entranceAge = null
    this.disposed = false
    const initial = samplePolyline(points, Infinity)
    this.totalDistance = initial.total
    this.distance = this.totalDistance * progress
    const pose = samplePolyline(points, this.distance)
    if (pose.point) this.wrapper.position.copy(pose.point).setY(floorY)
  }

  async load() {
    const gltf = await loadRobotAsset(this.modelAssetKey)
    if (this.disposed) return
    this.model = cloneSkeleton(gltf.scene)
    this.model.name = `${this.id} ${this.modelAssetKey}`
    if (this.modelAssetKey === DEFAULT_ROBOT_ASSET) {
      poseAgibotMapArms(this.model)
      this.model.rotation.y = AGIBOT_ROUTE_YAW
    }
    this.model.traverse((object) => {
      if (!object.isMesh) return
      object.userData.robotId = this.id
      object.castShadow = true
      object.receiveShadow = true
      const source = Array.isArray(object.material) ? object.material : [object.material]
      const materials = source.map((material) => {
        const clone = material.clone()
        clone.userData.originalEmissive = clone.emissive?.clone() || null
        clone.userData.originalEmissiveIntensity = clone.emissiveIntensity || 0
        clone.userData.originalOpacity = clone.opacity
        clone.userData.originalTransparent = clone.transparent
        return clone
      })
      object.material = Array.isArray(object.material) ? materials : materials[0]
    })
    this.model.updateMatrixWorld(true)
    const originalBounds = new THREE.Box3().setFromObject(this.model)
    const originalSize = originalBounds.getSize(new THREE.Vector3())
    const scale = originalSize.y > 0 ? this.targetHeight / originalSize.y : 1
    this.baseRobotScale.setScalar(scale)
    this.model.scale.copy(this.baseRobotScale).multiplyScalar(REALTIME_ROBOT_SCALE_MULTIPLIER)
    this.model.updateMatrixWorld(true)
    const scaled = new THREE.Box3().setFromObject(this.model)
    const center = scaled.getCenter(new THREE.Vector3())
    this.model.position.set(-center.x, -scaled.min.y, -center.z)
    this.model.updateMatrixWorld(true)
    this.boundsHeight = new THREE.Box3().setFromObject(this.model).getSize(new THREE.Vector3()).y
    this.wrapper.add(this.model)
    this.entranceAge = 0
    this.wrapper.scale.setScalar(0.94)

    this.hitTarget = new THREE.Mesh(
      new THREE.CylinderGeometry(
        ROBOT_HIT_TARGET.radius,
        ROBOT_HIT_TARGET.radius,
        ROBOT_HIT_TARGET.height,
        ROBOT_HIT_TARGET.segments,
      ),
      new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, depthWrite: false }),
    )
    this.hitTarget.name = `${this.id} Raycast Hit Target`
    this.hitTarget.position.y = ROBOT_HIT_TARGET.height / 2
    this.hitTarget.userData.robotId = this.id
    this.hitTarget.userData.isRobotHitTarget = true
    this.wrapper.add(this.hitTarget)

    if (gltf.animations.length) {
      this.mixer = new THREE.AnimationMixer(this.model)
      const clip = gltf.animations.find((entry) => /move|drive|wheel|walk/i.test(entry.name)) || gltf.animations[0]
      this.mixer.clipAction(clip).play()
    }
    this.applySelection()
  }

  setRoute(points, progress = this.progress) {
    this.points = points
    const sample = samplePolyline(points, Infinity)
    this.totalDistance = sample.total
    this.distance = this.totalDistance * progress
  }

  setSelected(selected) {
    this.selected = selected
    this.applySelection()
  }

  setFollowing(following) {
    this.following = Boolean(following)
  }

  setEmphasis(factor = 1) {
    this.emphasis = factor
    this.model?.traverse((object) => {
      if (!object.isMesh) return
      const materials = Array.isArray(object.material) ? object.material : [object.material]
      materials.forEach((material) => {
        const originalOpacity = material.userData.originalOpacity ?? 1
        material.opacity = originalOpacity * factor
        material.transparent = factor < 1 || material.userData.originalTransparent
      })
    })
    this.wrapper.visible = factor > 0
  }

  applySelection() {
    this.model?.traverse((object) => {
      if (!object.isMesh) return
      const materials = Array.isArray(object.material) ? object.material : [object.material]
      materials.forEach((material) => {
        if (!material.emissive) return
        material.emissive.copy(this.selected && !this.offline ? this.color : (material.userData.originalEmissive || new THREE.Color(0)))
        material.emissiveIntensity = this.selected && !this.offline ? 0.18 : material.userData.originalEmissiveIntensity
      })
    })
    this.setEmphasis(this.emphasis)
  }

  update(delta, camera, elapsed, doorController) {
    this.waitingForDoor = false
    if (this.entranceAge != null && this.entranceAge < 1.5) {
      this.entranceAge = Math.min(1.5, this.entranceAge + delta)
      const progress = this.entranceAge / 1.5
      const eased = 1 - ((1 - progress) ** 3)
      this.wrapper.scale.setScalar(0.94 + eased * 0.06)
    }
    if (this.points.length > 1 && this.totalDistance > 0) {
      // Check each small step so a slow frame cannot jump through a closed door.
      let remaining = Math.min(this.speed * Math.max(0, delta), this.totalDistance - this.distance)
      while (remaining > 1e-8) {
        const step = Math.min(remaining, 0.05)
        const next = samplePolyline(this.points, this.distance + step).point
        const current = samplePolyline(this.points, this.distance).point
        if (doorController && !doorController.canMove(current, next)) {
          this.waitingForDoor = true
          break
        }
        this.distance += step
        remaining -= step
      }
      const pose = samplePolyline(this.points, this.distance)
      this.wrapper.position.copy(pose.point).setY(this.floorY)
      const yaw = Math.atan2(pose.tangent.x, pose.tangent.z)
      this.targetQuaternion.setFromAxisAngle(THREE.Object3D.DEFAULT_UP, yaw)
      this.wrapper.quaternion.slerp(this.targetQuaternion, 1 - Math.exp(-8 * delta))
    }
    if (!this.waitingForDoor) this.mixer?.update(delta)
  }

  getWorldPosition() { return this.wrapper.getWorldPosition(new THREE.Vector3()) }
  getInfoAnchor() {
    return this.getWorldPosition().add(new THREE.Vector3(0, this.boundsHeight + 0.58, 0))
  }
  getForwardVector() {
    return new THREE.Vector3(0, 0, 1)
      .applyQuaternion(this.wrapper.getWorldQuaternion(new THREE.Quaternion()))
      .setY(0)
      .normalize()
  }
  getRouteState() {
    if (this.points.length < 2 || this.totalDistance <= 0) return { progress: 0, isFinalSegment: false }
    const lengths = this.points.slice(1).map((point, index) => point.distanceTo(this.points[index]))
    let remaining = THREE.MathUtils.clamp(this.distance, 0, this.totalDistance)
    let segmentIndex = 0
    for (; segmentIndex < lengths.length - 1 && remaining > lengths[segmentIndex]; segmentIndex += 1) {
      remaining -= lengths[segmentIndex]
    }
    return {
      progress: this.distance / this.totalDistance,
      segmentIndex,
      isFinalSegment: segmentIndex === lengths.length - 1,
    }
  }
  getPickables() {
    const result = []
    this.model?.traverse((object) => { if (object.isMesh) result.push(object) })
    if (this.hitTarget) result.push(this.hitTarget)
    return result
  }

  dispose() {
    this.disposed = true
    this.mixer?.stopAllAction()
    if (this.mixer && this.model) this.mixer.uncacheRoot(this.model)
    this.wrapper.removeFromParent()
    this.wrapper.traverse((object) => {
      if (object === this.hitTarget) object.geometry.dispose()
      const materials = Array.isArray(object.material) ? object.material : [object.material]
      materials.filter(Boolean).forEach((material) => material.dispose())
    })
  }
}
