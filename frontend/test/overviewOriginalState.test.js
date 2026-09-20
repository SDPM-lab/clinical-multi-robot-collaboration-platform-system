import { expect, it } from 'vitest'
import * as THREE from 'three'
import { captureOverviewOriginalState, restoreOverviewOriginalState } from '@/three/overviewOriginalState.js'
it('isolates shared materials and restores complete exported appearance and hidden groups repeatedly', () => {
  const root = new THREE.Group(), hidden = new THREE.Group()
  hidden.visible = false
  root.add(hidden)
  const texture = new THREE.Texture()
  const material = new THREE.MeshPhysicalMaterial({ color: '#92aaab', roughness: .23, metalness: .14, transmission: .64, opacity: .7, transparent: true, emissive: '#224466', emissiveIntensity: .4, map: texture, side: THREE.DoubleSide })
  const a = new THREE.Mesh(new THREE.BoxGeometry(), material), b = new THREE.Mesh(a.geometry, material)
  root.add(a, b)
  a.position.x = 3
  const resources = new Set()
  const states = captureOverviewOriginalState(root, m => resources.add(m))
  expect(a.material).not.toBe(b.material)
  for (let i = 0; i < 5; i++) {
    a.material.color.set('#ffffff'); a.material.opacity = .22; a.material.roughness = 1
    a.material.transmission = 0; a.material.emissiveIntensity = 5
    hidden.visible = true; a.position.x = 10
    restoreOverviewOriginalState(states)
    expect(hidden.visible).toBe(false)
    expect(a.position.x).toBe(3)
    for (const key of ['opacity', 'transparent', 'roughness', 'metalness', 'transmission', 'emissiveIntensity', 'side', 'map']) expect(a.material[key]).toBe(material[key])
    expect(a.material.color.equals(material.color)).toBe(true)
    expect(a.material.emissive.equals(material.emissive)).toBe(true)
  }
  resources.forEach(m => m.dispose()); a.geometry.dispose(); texture.dispose()
})
