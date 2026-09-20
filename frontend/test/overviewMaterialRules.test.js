import { describe, expect, it } from 'vitest'

import { classifyOverviewMaterial } from '@/three/overviewMaterialRules.js'
import { darkSceneTheme, lightSceneTheme } from '@/three/sceneTheme.js'

const object = (name, parent = null) => ({ name, parent })
const material = (name) => ({ name })

describe('overview material rules', () => {
  it('uses exact exported material names for architectural accents', () => {
    expect(classifyOverviewMaterial(
      object('ward_a_door__right__proxy'),
      material('MAT_RoomDoor_LightWood'),
    )).toBe('woodAccent')
    expect(classifyOverviewMaterial(
      object('consult_3_door__right__proxy'),
      material('MAT_RoomDoor_Frame.001'),
    )).toBe('woodAccent')
    expect(classifyOverviewMaterial(
      object('ward_a_door_frame'),
      material('MAT_RoomDoor_Frame'),
    )).toBe('woodAccentDark')
  })

  it('keeps walls, floors, glass, furniture, and equipment separate', () => {
    expect(classifyOverviewMaterial(object('wall'), material('MAT_Wall_WarmWhite'))).toBe('wall')
    expect(classifyOverviewMaterial(object('floor'), material('MAT_Hospital_Floor'))).toBe('floor')
    expect(classifyOverviewMaterial(object('entrance'), material('MAT_MainEntrance_Glass'))).toBe('glass')
    expect(classifyOverviewMaterial(object('sofa'), material('MAT_Chair_SaturatedOrange'))).toBe('furniture')
    expect(classifyOverviewMaterial(object('monitor'), material('MAT_BPM_Screen'))).toBe('equipment')
  })

  it('does not classify generic wood or panel names as a warm accent', () => {
    expect(classifyOverviewMaterial(
      object('BedsideTable_BackPanel_01'),
      material('MAT_Bedside_LightWood'),
    )).toBe('furniture')
    expect(classifyOverviewMaterial(
      object('CGMBed_ControlScreen_01'),
      material('MAT_CGM_ControlPanel'),
    )).toBe('equipment')
  })

  it('uses the requested limited palettes in both themes', () => {
    expect(lightSceneTheme.overview.wall).toBe(0xede8dc)
    expect(lightSceneTheme.overview.structure).toBe(0xc5bfb8)
    expect(lightSceneTheme.overview.furniture).toBe(0xb5b0a8)
    expect(lightSceneTheme.overview.equipment).toBe(0xa09b96)
    expect(lightSceneTheme.overview.woodAccent).toBe(0xd4be9a)
    expect(lightSceneTheme.overview.woodAccentDark).toBe(0xbfa07a)
    expect(darkSceneTheme.overview.woodAccent).toBe(0xc4a77e)
    expect(darkSceneTheme.overview.woodAccentDark).toBe(0xa98a63)
  })
})
