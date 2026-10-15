import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { Vector3 } from 'three'
import { AgibotArmAssembly } from '@/three/robot/AgibotArmAssembly.js'

describe('AGIBOT A2D mesh assembly', () => {
  it('moves only arm and gripper meshes and restores exact original local positions', async () => {
    const bytes = readFileSync('public/models/AGIBOT_A2D.glb')
    const gltf = await new GLTFLoader().parseAsync(new Uint8Array(bytes).buffer, '')
    const meshes = []
    gltf.scene.traverse(object => { if (object.isMesh) meshes.push(object) })
    expect(gltf.scene.getObjectByName('AGIBOT_A2D')).toBeTruthy()
    expect(meshes).toHaveLength(135)
    const original = new Map(meshes.map(mesh => [mesh, mesh.position.clone()]))
    const assembly = new AgibotArmAssembly(gltf.scene)
    expect(assembly.records).toHaveLength(124)
    assembly.set(1)
    expect(assembly.explodedBounds.getSize(new Vector3()).length()).toBeGreaterThan(assembly.assembledBounds.getSize(new Vector3()).length())
    for (const mesh of meshes.filter(mesh => !assembly.records.some(record => record.mesh === mesh))) {
      expect(mesh.position.equals(original.get(mesh))).toBe(true)
    }
    assembly.set(.3)
    assembly.set(.9)
    assembly.set(.1)
    assembly.set(0)
    for (const mesh of meshes) expect(mesh.position.equals(original.get(mesh))).toBe(true)
  })
})
