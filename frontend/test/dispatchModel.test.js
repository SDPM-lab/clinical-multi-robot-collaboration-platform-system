// @vitest-environment node
import { readFileSync } from 'node:fs'
import { afterAll, beforeAll, describe, expect, it } from 'vitest'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { dispatchLocations, dispatchRmfTransform, isDispatchPreview, modelObjectName, rmfToDispatch, validDispatchTransform } from '@/config/dispatchMap.js'
import { rmfToThree } from '@/config/rmfMapTransform.js'

let gltf
beforeAll(async () => {
  const bytes = readFileSync('public/models/L1__flat.glb')
  gltf = await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '')
})
afterAll(() => {
  const resources = new Set()
  gltf?.scenes.forEach((scene) => scene.traverse((object) => {
    if (object.geometry) resources.add(object.geometry)
    ;[object.material].flat().filter(Boolean).forEach((material) => resources.add(material))
  }))
  resources.forEach((resource) => resource.dispose())
})
describe('actual dispatch GLB', () => {
  it('loads the designated default scene and recognizes its preview ground', () => {
    expect(gltf.scene.name).toBe('L1_Solid_Block_Map_v5')
    const excluded = []
    gltf.scene.traverse((object) => { if (isDispatchPreview(object)) excluded.push(object) })
    expect(excluded).toHaveLength(1)
    expect(modelObjectName(excluded[0])).toBe('Preview_Ground_NOT_FOR_EXPORT')
    expect(isDispatchPreview({ isCamera: true })).toBe(true)
    expect(isDispatchPreview({ isLight: true })).toBe(true)
  })
  it('resolves selectable rooms in the default scene and retains colored route materials', () => {
    const names = new Set(), materialNames = new Set()
    gltf.scene.traverse((object) => {
      names.add(modelObjectName(object))
      ;[object.material].flat().filter(Boolean).forEach((material) => materialNames.add(material.name))
    })
    Object.values(dispatchLocations).forEach(({ room }) => expect(names.has(`Room_${room}`)).toBe(true))
    expect([...materialNames].some((name) => name.startsWith('HM_Route_Green'))).toBe(true)
  })
})
it('reuses the Traffic Editor transform and applies a shared adjustable transform', () => {
  const point = { x: 12, y: -8, level: 'L1' }
  expect(rmfToDispatch(point)).toEqual(rmfToThree(point, dispatchRmfTransform))
  const transform = { ...dispatchRmfTransform, scale: 2, rotation: Math.PI / 2, offsetX: 3, offsetZ: 4 }
  const result = rmfToDispatch(point, transform)
  expect(result.x).toBeCloseTo(-13)
  expect(result.z).toBeCloseTo(28)
  expect(rmfToDispatch({ ...point, level: 'L2' })).toBeNull()
  expect(validDispatchTransform({ ...transform, scale: NaN })).toBe(false)
  expect(rmfToDispatch(point, { ...transform, scale: 0 })).toBeNull()
})
