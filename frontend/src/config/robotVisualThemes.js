import { visualTokens, colorHex, colorAlpha } from './visualTokens.js'

const robotPalette = (robotId, color) => Object.freeze({
  robotId, main: color, css: color, mainOklch: color, mainHex: colorHex(color),
  completed: color, completedHex: colorHex(color),
  soft: colorAlpha(color, .12), border: colorAlpha(color, .42),
  glow: colorAlpha(color, .12), glowHex: colorHex(color),
})
export const robotTheme = Object.freeze({
  primary: robotPalette('R01', visualTokens.primary),
  secondary: robotPalette('R02', visualTokens.secondary),
  third: robotPalette('R03', visualTokens.neutral),
  success: Object.freeze({ main: visualTokens.neutral, mainHex: colorHex(visualTokens.neutral) }),
})
export const semanticTheme = Object.freeze({
  destination: visualTokens.primary, destinationHex: colorHex(visualTokens.primary),
  success: visualTokens.neutral, successHex: colorHex(visualTokens.neutral),
  warning: visualTokens.secondary, error: visualTokens.error,
  chargingStation: visualTokens.chargingStation,
  chargingStationHex: colorHex(visualTokens.chargingStation),
  chargingStationDark: visualTokens.chargingStation,
  chargingStationSoft: colorAlpha(visualTokens.chargingStation, .12),
  chargingStationBorder: colorAlpha(visualTokens.chargingStation, .48),
})
const withCardTokens = theme => Object.freeze({
  ...theme, cardBackground: theme.soft, cardBorder: theme.border, cardGlow: theme.soft,
})
const displayThemes = Object.freeze({
  R01: withCardTokens(robotTheme.primary),
  R02: withCardTokens(robotTheme.secondary),
  R03: withCardTokens(robotTheme.third),
  R04: withCardTokens(robotPalette('R04', '#5D9DD3')),
  R05: withCardTokens(robotPalette('R05', '#8F79BD')),
  R06: withCardTokens(robotPalette('R06', '#58A691')),
  R07: withCardTokens(robotPalette('R07', '#CE718A')),
})
// Visual aliases only: canonical backend IDs are never rewritten.
export const robotVisualThemes = Object.freeze({
  ...displayThemes,
  ...Object.fromEntries(['C01', 'C02', 'M01', 'M02', 'W01', 'W02', 'W03'].map((code, index) => [
    code,
    displayThemes[`R${String(index + 1).padStart(2, '0')}`],
  ])),
  ...Object.fromEntries(Array.from({length:7},(_,index)=>[
    index===0 ? 'robot-a' : index===1 ? 'robot-b' : `robot-hospital_robot_${index+1}`,
    displayThemes[`R${String(index+1).padStart(2,'0')}`],
  ])),
})
export const fallbackRobotVisualTheme = withCardTokens(robotPalette(null, visualTokens.neutral))
export const semanticColors = Object.freeze({ ...semanticTheme })
export const getRobotVisualTheme = robotId => robotVisualThemes[robotId] || fallbackRobotVisualTheme
