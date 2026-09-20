export const robotTheme = Object.freeze({
  primary: Object.freeze({
    robotId: 'R01',
    main: '#CF7540',
    css: '#CF7540',
    mainHex: 0xcf7540,
    completed: '#B85F32',
    completedHex: 0xb85f32,
    soft: 'rgba(207, 117, 64, 0.16)',
    border: 'rgba(207, 117, 64, 0.42)',
    glow: 'rgba(207, 117, 64, 0.22)',
    glowHex: 0xcf7540,
  }),
  secondary: Object.freeze({
    robotId: 'R02',
    main: '#D5AD4E',
    mainHex: 0xd5ad4e,
    completed: '#A9853A',
    completedHex: 0xa9853a,
    soft: 'rgba(213, 173, 78, 0.15)',
    border: 'rgba(213, 173, 78, 0.52)',
    glow: 'rgba(213, 173, 78, 0.22)',
    glowHex: 0xd5ad4e,
  }),
  third: Object.freeze({
    robotId: 'R03',
    main: '#4F9F91',
    mainOklch: '#4F9F91',
    css: '#4F9F91',
    mainHex: 0x4f9f91,
    completed: '#3B776D',
    completedHex: 0x3b776d,
    soft: 'rgba(79, 159, 145, 0.15)',
    border: 'rgba(79, 159, 145, 0.50)',
    glow: 'rgba(79, 159, 145, 0.22)',
    glowHex: 0x4f9f91,
  }),
  success: Object.freeze({ main: '#6F9B7B', mainHex: 0x6f9b7b }),
})

export const semanticTheme = Object.freeze({
  destination: '#C96561',
  destinationHex: 0xc96561,
  success: '#6F9B7B',
  successHex: 0x6f9b7b,
  warning: '#C59A52',
  error: '#C96561',
  chargingStation: '#8F9692',
  chargingStationHex: 0x8f9692,
  chargingStationDark: '#B0B5B2',
  chargingStationSoft: 'rgba(143, 150, 146, 0.12)',
  chargingStationBorder: 'rgba(143, 150, 146, 0.48)',
})

const withCardTokens = (theme) => Object.freeze({
  ...theme,
  cardBackground: theme.soft,
  cardBorder: theme.border || theme.glow,
  cardGlow: theme.soft,
})

export const robotVisualThemes = Object.freeze({
  R01: withCardTokens(robotTheme.primary),
  R02: withCardTokens(robotTheme.secondary),
  R03: withCardTokens(robotTheme.third),
})

export const fallbackRobotVisualTheme = Object.freeze({
  main: '#9A72DC',
  mainHex: 0x9a72dc,
  completed: '#704CAB',
  completedHex: 0x704cab,
  soft: 'rgba(154, 114, 220, 0.20)',
  glow: '#B995F0',
  glowHex: 0xb995f0,
  cardBackground: 'rgba(154, 114, 220, 0.82)',
  cardBorder: 'rgba(205, 181, 244, 0.94)',
  cardGlow: 'rgba(154, 114, 220, 0.38)',
})

export const semanticColors = Object.freeze({
  ...semanticTheme,
})

export const getRobotVisualTheme = (robotId) => robotVisualThemes[robotId] || fallbackRobotVisualTheme
