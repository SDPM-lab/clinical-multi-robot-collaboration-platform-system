import { getSceneTheme } from '@/three/sceneTheme.js'

const overviewStructure = Object.freeze({
  key: Object.freeze({
    position: Object.freeze([1.6, 2.6, 0.4]),
    castShadow: true,
    shadowIntensity: 0.88,
    shadowBias: -0.0001,
    shadowNormalBias: 0.015,
  }),
  fill: Object.freeze({ position: Object.freeze([-1, 1.25, -1]) }),
})

const realtimeStructure = Object.freeze({
  key: Object.freeze({
    position: Object.freeze([1, 2, 1]),
    castShadow: true,
    shadowIntensity: 0.65,
    shadowBias: -0.00005,
    shadowNormalBias: 0.025,
  }),
  fill: Object.freeze({ position: Object.freeze([-1, 1.25, -1]) }),
})

export function getSceneLighting(mode, theme = 'light') {
  const sceneTheme = getSceneTheme(theme)
  const variant = mode === 'original' ? 'original' : 'overview'
  const themedLighting = sceneTheme.lighting[variant]
  const structure = mode === 'original' ? realtimeStructure : overviewStructure

  return {
    background: mode === 'original' ? sceneTheme.originalBackground : sceneTheme.background,
    toneMappingExposure: themedLighting.toneMappingExposure,
    hemisphere: {
      skyColor: themedLighting.hemisphereSkyColor,
      groundColor: themedLighting.hemisphereGroundColor,
      intensity: themedLighting.hemisphereIntensity,
    },
    ambient: {
      color: themedLighting.ambientColor,
      intensity: themedLighting.ambientIntensity,
    },
    key: {
      ...structure.key,
      color: themedLighting.keyColor,
      intensity: themedLighting.keyIntensity,
    },
    fill: {
      ...structure.fill,
      color: themedLighting.fillColor,
      intensity: themedLighting.fillIntensity,
    },
  }
}
