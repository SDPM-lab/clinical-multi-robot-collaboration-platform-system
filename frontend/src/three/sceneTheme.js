const freezeTheme = (theme) => Object.freeze({
  ...theme,
  overview: Object.freeze(theme.overview),
  lighting: Object.freeze({
    overview: Object.freeze(theme.lighting.overview),
    original: Object.freeze(theme.lighting.original),
  }),
})

export const overviewLightPalette = Object.freeze({
  background: 0xe2d9c4,
  wall: 0xede8dc,
  floor: 0xcecac0,
  structure: 0xc5bfb8,
  furniture: 0xb5b0a8,
  equipment: 0xa09b96,
  woodAccent: 0xd4be9a,
  woodAccentDark: 0xbfa07a,
  glass: 0xa4c8e4,
})

export const overviewDarkPalette = Object.freeze({
  background: 0x111311,
  wall: 0xa7aaa5,
  floor: 0x7e827e,
  structure: 0x8e928e,
  furniture: 0x919591,
  equipment: 0xb9bcb7,
  woodAccent: 0xc4a77e,
  woodAccentDark: 0xa98a63,
  glass: 0x5a8aaa,
})

export const lightSceneTheme = freezeTheme({
  background: overviewLightPalette.background,
  originalBackground: overviewLightPalette.background,
  overview: overviewLightPalette,
  lighting: {
    overview: {
      toneMappingExposure: 1.22,
      hemisphereSkyColor: 0xf0f4f8,
      hemisphereGroundColor: 0xc8ccd0,
      hemisphereIntensity: 0.96,
      ambientColor: 0xffffff,
      ambientIntensity: 0.18,
      keyColor: 0xffcc88,
      keyIntensity: 1.72,
      fillColor: 0xffe0c0,
      fillIntensity: 0.22,
    },
    original: {
      toneMappingExposure: 1.16,
      hemisphereSkyColor: 0xffffff,
      hemisphereGroundColor: 0xdfe3e1,
      hemisphereIntensity: 2,
      ambientColor: 0xffffff,
      ambientIntensity: 0.35,
      keyColor: 0xffffff,
      keyIntensity: 1.75,
      fillColor: 0xffffff,
      fillIntensity: 0.8,
    },
  },
})

export const darkSceneTheme = freezeTheme({
  background: overviewDarkPalette.background,
  originalBackground: overviewDarkPalette.background,
  overview: overviewDarkPalette,
  lighting: {
    overview: {
      toneMappingExposure: 1.04,
      hemisphereSkyColor: 0xe0e4e0,
      hemisphereGroundColor: 0x555a57,
      hemisphereIntensity: 1.42,
      ambientColor: 0xe7e9e5,
      ambientIntensity: 0.44,
      keyColor: 0xf0f1ed,
      keyIntensity: 1.08,
      fillColor: 0xd4d9d4,
      fillIntensity: 0.58,
    },
    original: {
      toneMappingExposure: 1.08,
      hemisphereSkyColor: 0xe4e8e5,
      hemisphereGroundColor: 0x3f4442,
      hemisphereIntensity: 1.55,
      ambientColor: 0xe3e6e3,
      ambientIntensity: 0.55,
      keyColor: 0xf0f1ee,
      keyIntensity: 1.45,
      fillColor: 0xcbd0cc,
      fillIntensity: 0.68,
    },
  },
})

export function getSceneTheme(theme) {
  return theme === 'dark' ? darkSceneTheme : lightSceneTheme
}
