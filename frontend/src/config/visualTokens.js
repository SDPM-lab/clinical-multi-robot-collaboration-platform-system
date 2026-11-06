// Shared UI palette. Robot series retain the approved Overview chart colors.
export const visualTokens = Object.freeze({
  primary: '#FB9966', secondary: '#FBE251', neutral: '#77746D',
  chargingStation: '#AB3B3A',
  text: '#343434', textSecondary: '#6D6D6D', textMuted: '#929292', textDisabled: '#B5B5B5',
  darkText: '#EFEFEF', darkTextSecondary: '#C2C2C2', darkTextMuted: '#939393', darkTextDisabled: '#626262',
  white: '#FFFFFF', error: '#C96561',
})
export const colorHex = hex => parseInt(hex.slice(1), 16)
export const colorRgb = hex => hex.slice(1).match(/.{2}/g).map(value => parseInt(value, 16)).join(',')
export const colorAlpha = (hex, opacity) => `rgba(${colorRgb(hex)},${opacity})`
export const robotSeriesColors = Object.freeze([visualTokens.primary, visualTokens.secondary, visualTokens.neutral])

// Base tokens are installed on <html>; light/dark semantic aliases live in theme.css.
export const globalVisualVars = Object.freeze(Object.fromEntries(
  Object.entries(visualTokens).flatMap(([name, color]) => {
    const key = name.replace(/[A-Z]/g, letter => `-${letter.toLowerCase()}`)
    return [[`--color-${key}`, color], [`--color-${key}-rgb`, colorRgb(color)]]
  }),
))
export function installVisualTokens(element) {
  for (const [name, value] of Object.entries(globalVisualVars)) element.style.setProperty(name, value)
}
