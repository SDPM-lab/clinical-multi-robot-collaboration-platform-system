// Demo defaults; replace these thresholds with the actual manufacturer's specifications.
export const robotTemperatureThresholds = Object.freeze({ normalMax: 54, warningMax: 69, criticalMin: 70 })
export const temperatureGradient = Object.freeze([
  Object.freeze({ stop: 0, color: '#72A89C' }),
  Object.freeze({ stop: .5, color: '#A8B87A' }),
  Object.freeze({ stop: .72, color: '#D1A45F' }),
  Object.freeze({ stop: 1, color: '#B9635D' }),
])
export const thermalState = (value) => !Number.isFinite(value) ? 'unknown' : value >= robotTemperatureThresholds.criticalMin ? 'critical' : value > robotTemperatureThresholds.normalMax ? 'warning' : 'normal'
export const batteryLiquidPalette = Object.freeze({
  normalTop: '#D29A72', normalBottom: '#A96547',
  warningTop: '#D7B66B', warningBottom: '#A9833F',
  criticalTop: '#C97872', criticalBottom: '#98524F',
  chargingTop: '#8BBAB0', chargingBottom: '#4F8178',
})
export const batteryLiquidColors = (value, charging = false) => charging
  ? [batteryLiquidPalette.chargingTop, batteryLiquidPalette.chargingBottom]
  : value <= 20
    ? [batteryLiquidPalette.criticalTop, batteryLiquidPalette.criticalBottom]
    : value <= 40
      ? [batteryLiquidPalette.warningTop, batteryLiquidPalette.warningBottom]
      : [batteryLiquidPalette.normalTop, batteryLiquidPalette.normalBottom]
export const batteryColor = (value, charging = false) => charging ? '#4F9F91' : value < 20 ? '#C96561' : value <= 40 ? '#D5AD4E' : '#C96F3B'
// Confirmed from robot.glb: these three meshes occupy the lowest 7% of the model.
// They are chassis/rolling assemblies, NOT individually identified motor sensors.
export const robotThermalZones = Object.freeze({
  chassis: ['Layer_03001', 'Layer_03002', 'Layer_03003'],
  leftMotor: [], rightMotor: [], battery: [], controller: [],
})
// GLTFLoader sanitizes spaces to underscores and removes dots. No independent battery or reliable
// battery location exists in the source asset. Do not invent a glowing compartment.
// The single outer shell spans y=.813..25.354 in source geometry; only its
// bottom (y<6) is used as a visible chassis surface proxy for aggregate heat.
export const robotThermalSurface = Object.freeze({ object: 'Layer_01001', maxLocalHeight: 6 })
export const robotBatteryZoneRules = Object.freeze([])
export const chargingLabels = Object.freeze({ idle: '前往充電', confirming: '確認充電', dispatching: '建立模擬命令中', navigating: '正在前往充電站', docking: '正在對接充電座', charging: '充電中', completed: '充電完成', failed: '充電命令失敗' })
export const robotPresentation = Object.freeze({ entranceMs: 4100, switchMs: 420, modelHeight: 2.8, camera: [2.6, .8, 6.4], fov: 30 })
export const stageLighting = Object.freeze({
  light: { spotlight: 0xfff3df, rim: 0xf2c6a4, intensity: 38 },
  dark: { spotlight: 0xffe1bd, rim: 0xc96f3b, intensity: 46 },
})
