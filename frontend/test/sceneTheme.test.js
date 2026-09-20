import { describe, expect, it } from 'vitest'

import { getSceneLighting } from '@/three/lighting/sceneLighting.js'
import {
  darkSceneTheme,
  getSceneTheme,
  lightSceneTheme,
} from '@/three/sceneTheme.js'

describe('shared 3D scene themes', () => {
  it('uses the shared warm application background while preserving realtime depth', () => {
    expect(getSceneLighting('overview', 'light').background).toBe(0xe2d9c4)
    expect(getSceneLighting('original', 'light').background).toBe(0xe2d9c4)
    expect(getSceneLighting('overview', 'dark').background).toBe(0x111311)
    expect(getSceneLighting('original', 'dark').background).toBe(0x111311)
  })

  it('selects the expected centralized theme', () => {
    expect(getSceneTheme('light')).toBe(lightSceneTheme)
    expect(getSceneTheme('dark')).toBe(darkSceneTheme)
  })

  it('keeps stronger ambient support for the original-material dark scene', () => {
    const overview = getSceneLighting('overview', 'dark')
    const realtime = getSceneLighting('original', 'dark')

    expect(realtime.ambient.intensity).toBeGreaterThan(overview.ambient.intensity)
    expect(realtime.fill.intensity).toBeGreaterThan(overview.fill.intensity)
  })
})
