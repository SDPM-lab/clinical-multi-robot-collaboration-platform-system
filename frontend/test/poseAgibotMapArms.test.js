import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { clone } from 'three/addons/utils/SkeletonUtils.js'
import { poseAgibotMapArms } from '@/three/robot/poseAgibotMapArms.js'

const boundsFor = (root, predicate) => {
  const bounds = new THREE.Box3()
  root.traverse(mesh => { if (mesh.isMesh && predicate(mesh)) bounds.expandByObject(mesh) })
  return bounds
}

describe('AGIBOT realtime-map parked arms', () => {
  it('lowers both hands without changing the shared source model or placing them below the base', async () => {
    const bytes = readFileSync('public/models/AGIBOT_A2D.glb')
    const source = (await new GLTFLoader().parseAsync(new Uint8Array(bytes).buffer, '')).scene
    const model = clone(source)
    const base = boundsFor(model, mesh => mesh.userData.disassembly_zone === 'base')
    const sourceHands = {}
    for (const side of ['left', 'right']) {
      const matches = mesh => String(mesh.userData.source_link || '').startsWith(`${side}_`)
      sourceHands[side] = boundsFor(source, matches).getCenter(new THREE.Vector3())
    }

    expect(poseAgibotMapArms(model)).toBe(true)
    for (const side of ['left', 'right']) {
      const matches = mesh => String(mesh.userData.source_link || '').startsWith(`${side}_`)
      const hand = boundsFor(model, matches)
      expect(hand.getCenter(new THREE.Vector3()).y).toBeLessThan(sourceHands[side].y - 0.35)
      expect(hand.min.y).toBeGreaterThan(base.min.y - 0.03)
      expect(boundsFor(source, matches).getCenter(new THREE.Vector3()).distanceTo(sourceHands[side])).toBeLessThan(1e-6)
    }
    expect(boundsFor(model, mesh => mesh.userData.disassembly_zone === 'base').equals(base)).toBe(true)
  })
})
