import { Box3, BoxGeometry, Group, Mesh, MeshBasicMaterial } from 'three'
import { describe, expect, it } from 'vitest'
import {
  buildOverviewFloorMapping,
  floorIdFromOverviewName,
  isOverviewFloorCameraNode,
  isOverviewCeilingLightNode,
  isOverviewFloorIsolationExcludedNode,
  modelLoadPercentage,
  normalizeOverviewNodeName,
} from '@/three/clinicFloorMapping.js'

const meshAt = (name, y) => {
  const mesh = new Mesh(new BoxGeometry(1, 1, 1), new MeshBasicMaterial())
  mesh.name = name
  mesh.position.y = y
  return mesh
}

describe('clinic overview GLB floor mapping', () => {
  it('derives display progress from GLTFLoader progress events without completing early', () => {
    expect(modelLoadPercentage({ loaded: 495, total: 1000 })).toBe(50)
    expect(modelLoadPercentage({ loaded: 1000, total: 1000 })).toBe(99)
    expect(modelLoadPercentage({ loaded: 500, total: 0 })).toBe(0)
  })
  it('normalizes Blender suffixes and recognizes current and common floor names', () => {
    expect(normalizeOverviewNodeName(' Floor_2-Slab.001 ')).toBe('floor2slab')
    expect(floorIdFromOverviewName('Floor_1_Slab')).toBe('1')
    expect(floorIdFromOverviewName('RightGlass_F2_Glass_01')).toBe('2')
    expect(floorIdFromOverviewName('F3_Main_Mullion_04')).toBe('3')
    expect(floorIdFromOverviewName('First Floor')).toBe('1')
    expect(floorIdFromOverviewName('Level_03.001')).toBe('3')
    expect(floorIdFromOverviewName('Hospital_Cross_V')).toBe('1')
  })

  it('keeps site objects common and uses height fallback only for unlabelled building pieces', () => {
    const root = new Group()
    root.add(meshAt('F1_Main_Glass_01', 1.5), meshAt('Unlabelled_Window', 4.8), meshAt('Roof_Slab', 9.6), meshAt('Tree_Right_Main', 5), meshAt('Site_Base', 0))
    const { groups, common } = buildOverviewFloorMapping(root, Box3)
    expect(groups[1].map(({ name }) => name)).toContain('F1_Main_Glass_01')
    expect(groups[2].map(({ name }) => name)).toContain('Unlabelled_Window')
    expect(groups[3].map(({ name }) => name)).toContain('Roof_Slab')
    expect(common.map(({ name }) => name)).toContain('Tree_Right_Main')
    expect(common.map(({ name }) => name)).toContain('Site_Base')
  })

  it('excludes only ceiling lights while preserving the complete floor shell', () => {
    expect(isOverviewFloorIsolationExcludedNode('Roof_Slab')).toBe(false)
    expect(isOverviewFloorIsolationExcludedNode('Third_Floor_Dark_Soffit')).toBe(false)
    expect(isOverviewFloorIsolationExcludedNode('Web_F2_CeilingStrip_03')).toBe(true)
    expect(isOverviewFloorIsolationExcludedNode('F3_Light_0.35_1.0')).toBe(true)
    expect(isOverviewFloorIsolationExcludedNode('F2_Main_Glass_01')).toBe(false)
    expect(isOverviewFloorCameraNode('Floor_2_Slab')).toBe(true)
    expect(isOverviewFloorCameraNode('Web_F2_CeilingStrip_01')).toBe(false)
    expect(isOverviewFloorCameraNode('F2_Main_Mullion_04')).toBe(true)
  })

  it('collects complete floor descendants separately from ceiling light meshes', () => {
    const root = new Group()
    const structure = new Group()
    structure.name = 'F2_STRUCTURE'
    structure.add(meshAt('Exterior_Wall', 0), meshAt('Window_Glass', 0), meshAt('Balcony_Railing', 0))
    const lights = new Group()
    lights.name = 'F2_CEILING_LIGHTS'
    lights.add(meshAt('LED_Strip', 0))
    root.add(structure, lights)
    const mapping = buildOverviewFloorMapping(root, Box3)
    expect(mapping.floorStructureGroups[2].map(({ name }) => name)).toEqual(['Exterior_Wall', 'Window_Glass', 'Balcony_Railing'])
    expect(mapping.ceilingLightMeshes.map(({ name }) => name)).toEqual(['LED_Strip'])
    expect(isOverviewCeilingLightNode('Ceiling_Slab')).toBe(false)
    expect(isOverviewCeilingLightNode('Ceiling_Light_03')).toBe(true)
  })
})
