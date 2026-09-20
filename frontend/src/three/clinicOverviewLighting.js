import * as THREE from 'three'

export const overviewLighting = Object.freeze({ exposure: 0.88, environment: 0.74, hemisphere: 0.35, ambient: 0.18, key: 1.35, fill: 0.32 })

export function addOverviewLighting(scene) {
  const hemisphere = new THREE.HemisphereLight(0xf2f5f4, 0x52605c, overviewLighting.hemisphere)
  hemisphere.name = 'overviewHemisphere'
  const ambient = new THREE.AmbientLight(0xffffff, overviewLighting.ambient)
  ambient.name = 'overviewAmbient'
  const key = new THREE.DirectionalLight(0xffffff, overviewLighting.key)
  key.name = 'overviewKey'
  key.position.set(10, 15, 12)
  key.castShadow = true
  key.shadow.mapSize.set(2048, 2048)
  key.shadow.bias = -0.00015
  key.shadow.normalBias = 0.025
  key.shadow.intensity = 0.72
  key.shadow.radius = 3
  const fill = new THREE.DirectionalLight(0xe7edf0, overviewLighting.fill)
  fill.name = 'overviewFill'
  fill.position.set(-9, 7, 5)
  scene.add(hemisphere, ambient, key, key.target, fill, fill.target)
}

// Fit the shadow frustum in light space, including the transformed model footprint.
export function fitOverviewShadow(scene, root) {
  if (!root) return
  const bounds = new THREE.Box3().setFromObject(root)
  if (bounds.isEmpty()) return
  const center = bounds.getCenter(new THREE.Vector3())
  const radius = bounds.getSize(new THREE.Vector3()).length() / 2
  const key = scene.getObjectByName('overviewKey')
  if (!key) return
  key.position.copy(center).addScaledVector(new THREE.Vector3(10, 15, 12).normalize(), radius * 2)
  for (const name of ['overviewKey', 'overviewFill']) {
    const light = scene.getObjectByName(name)
    light.target.position.copy(center)
    light.target.updateMatrixWorld()
    light.updateMatrixWorld()
  }
  const camera = key.shadow.camera
  camera.position.copy(key.position)
  camera.lookAt(center)
  camera.updateMatrixWorld()
  const lightBounds = new THREE.Box3()
  for (const x of [bounds.min.x, bounds.max.x])
    for (const y of [bounds.min.y, bounds.max.y])
      for (const z of [bounds.min.z, bounds.max.z])
        lightBounds.expandByPoint(new THREE.Vector3(x, y, z).applyMatrix4(camera.matrixWorldInverse))
  const padding = radius * 0.05
  camera.left = lightBounds.min.x - padding
  camera.right = lightBounds.max.x + padding
  camera.bottom = lightBounds.min.y - padding
  camera.top = lightBounds.max.y + padding
  camera.near = Math.max(0.1, -lightBounds.max.z - padding)
  camera.far = -lightBounds.min.z + padding
  camera.updateProjectionMatrix()
  key.shadow.needsUpdate = true
}
