import { visualTokens, robotSeriesColors, colorRgb, colorAlpha } from '@/config/visualTokens.js'

// Compatibility aliases for existing Overview consumers; colors come from the global palette.
export const overviewPalette = Object.freeze({
  accent: visualTokens.primary, yellow: visualTokens.secondary, ink: visualTokens.text,
  accentText: visualTokens.primary, accentSoft: colorAlpha(visualTokens.primary, .12),
  yellowText: visualTokens.neutral, neutral: visualTokens.neutral,
})
export const overviewRobotColors = robotSeriesColors
export const overviewBuildingColors = Object.freeze({
  CTX_Building_White: '#FFFFFF', CTX_Building_Light: '#FCFCFA',
  CTX_Building_Mid: '#F7F8F5', CTX_Roof: '#F0F2EE',
})
// A small neutral fill lifts only the context buildings' unlit faces.
export const overviewBuildingFill = Object.freeze({ color: '#FFFFFF', intensity: .42 })
export const overviewThemeVars = Object.freeze({
  '--overview-completion-backdrop': 'blur(2px)',
  '--overview-accent': overviewPalette.accent,
  '--overview-yellow': overviewPalette.yellow,
  '--overview-ink': overviewPalette.ink,
  '--overview-accent-text': overviewPalette.accentText,
  '--overview-accent-soft': overviewPalette.accentSoft,
  '--overview-yellow-text': overviewPalette.yellowText,
  '--overview-neutral': overviewPalette.neutral,
  '--overview-accent-rgb': colorRgb(visualTokens.primary),
  '--overview-yellow-rgb': colorRgb(visualTokens.secondary),
})
