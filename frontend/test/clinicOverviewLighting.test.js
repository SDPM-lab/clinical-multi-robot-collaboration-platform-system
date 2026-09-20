import { expect, it } from 'vitest'
import * as THREE from 'three'
import { addOverviewLighting, fitOverviewShadow, overviewLighting } from '@/three/clinicOverviewLighting.js'

it('fits every transformed model corner inside the shadow camera', () => {
  const scene = new THREE.Scene()
  addOverviewLighting(scene)
  const root = new THREE.Mesh(new THREE.BoxGeometry(24, 10, 18), new THREE.MeshStandardMaterial())
  root.position.set(-2, 3.4, -0.7)
  root.rotation.y = 0.35
  root.scale.setScalar(0.81)
  scene.add(root)
  fitOverviewShadow(scene, root)
  const bounds = new THREE.Box3().setFromObject(root)
  const key = scene.getObjectByName('overviewKey')
  for (const x of [bounds.min.x, bounds.max.x])
    for (const y of [bounds.min.y, bounds.max.y])
      for (const z of [bounds.min.z, bounds.max.z]) {
        const projected = new THREE.Vector3(x, y, z).project(key.shadow.camera)
        expect(Math.abs(projected.x)).toBeLessThan(1)
        expect(Math.abs(projected.y)).toBeLessThan(1)
        expect(Math.abs(projected.z)).toBeLessThan(1)
      }
  expect(scene.children.filter(o => o.castShadow && o.isLight)).toHaveLength(1)
  expect(overviewLighting).toMatchObject({ exposure: 0.88, environment: 0.74, hemisphere: 0.35, ambient: 0.18, key: 1.35, fill: 0.32 })
  expect(scene.getObjectByName('overviewHemisphere').color.getHex()).toBe(0xf2f5f4)
  expect(scene.getObjectByName('overviewAmbient').intensity).toBe(0.18)
  expect(scene.getObjectByName('overviewKey').color.getHex()).toBe(0xffffff)
  expect(scene.getObjectByName('overviewFill').color.getHex()).toBe(0xe7edf0)
  root.geometry.dispose()
  root.material.dispose()
  scene.traverse(o => { if (o.isLight) o.dispose() })
})
