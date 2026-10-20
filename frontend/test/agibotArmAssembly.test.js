import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { AgibotArmAssembly } from '@/three/robot/AgibotArmAssembly.js'

const activeZones = new Set(['arms', 'head', 'base'])
const keys = ['l', 'r', 'head', 'base']

describe('AGIBOT A2D disassembly zones', () => {
  it('reads every mesh zone from the current GLB and restores exact local positions', async () => {
    const bytes = readFileSync('public/models/AGIBOT_A2D.glb')
    const gltf = await new GLTFLoader().parseAsync(new Uint8Array(bytes).buffer, '')
    const meshes = []
    gltf.scene.traverse(object => { if (object.isMesh) meshes.push(object) })
    expect(gltf.scene.getObjectByName('AGIBOT_A2D')).toBeTruthy()
    expect(meshes).toHaveLength(307)
    const originals = new Map(meshes.map(mesh => [mesh, mesh.position.clone()]))
    const counts = Object.groupBy(meshes, mesh => mesh.userData.disassembly_zone || 'unassigned')
    expect(counts.arms.length).toBeGreaterThan(0)
    expect(counts.head.length).toBeGreaterThan(0)
    expect(counts.base.length).toBeGreaterThan(0)
    expect(counts.mast.length).toBeGreaterThan(0)

    const assembly = new AgibotArmAssembly(gltf.scene)
    expect(assembly.records).toHaveLength(meshes.filter(mesh => activeZones.has(mesh.userData.disassembly_zone)).length)
    expect(assembly.records.filter(record => record.key === 'l' || record.key === 'r')).toHaveLength(counts.arms.length)
    expect(assembly.records.filter(record => record.key === 'head')).toHaveLength(counts.head.length)
    expect(assembly.records.filter(record => record.key === 'base')).toHaveLength(counts.base.length)

    for (const key of keys) {
      assembly.setZones({ [key]: 1 })
      expect(assembly.zoneBounds(key).isEmpty()).toBe(false)
      expect(assembly.records.some(record => record.key === key && !record.mesh.position.equals(originals.get(record.mesh)))).toBe(true)
      for (const mesh of meshes) {
        if (assembly.records.some(record => record.mesh === mesh && record.key === key)) continue
        expect(mesh.position.equals(originals.get(mesh))).toBe(true)
      }
      assembly.setZones({ [key]: .35 })
      const partial = new Map(assembly.records.filter(record => record.key === key).map(record => [record.mesh, record.mesh.position.clone()]))
      assembly.setZones({ [key]: .35 })
      for (const [mesh, position] of partial) expect(mesh.position.equals(position)).toBe(true)
      assembly.setZones({})
      for (const mesh of meshes) expect(mesh.position.equals(originals.get(mesh))).toBe(true)
    }
  })
})
