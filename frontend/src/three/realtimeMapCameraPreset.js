export const REALTIME_MAP_CAMERA_PRESET_STORAGE_KEY = 'hospital-rmf-realtime-map-camera-preset'

export const DEFAULT_REALTIME_MAP_CAMERA_PRESET = Object.freeze({
  positionOffset: Object.freeze([
    -0.3833631499011069,
    20.83812899610055,
    21.028162414465722,
  ]),
  targetOffset: Object.freeze([
    -0.4330170929945508,
    -1.6395162024072834,
    0.5890622293399864,
  ]),
  zoom: 1,
})

const isVector3 = (value) => (
  Array.isArray(value)
  && value.length === 3
  && value.every(Number.isFinite)
)

export function isRealtimeMapCameraPreset(value) {
  return Boolean(
    value
    && isVector3(value.positionOffset)
    && isVector3(value.targetOffset)
    && Number.isFinite(value.zoom)
    && value.zoom > 0,
  )
}

export function readStoredRealtimeMapCameraPreset() {
  try {
    const value = JSON.parse(localStorage.getItem(REALTIME_MAP_CAMERA_PRESET_STORAGE_KEY))
    return isRealtimeMapCameraPreset(value) ? value : null
  } catch {
    return null
  }
}

export function storeRealtimeMapCameraPreset(preset) {
  localStorage.setItem(REALTIME_MAP_CAMERA_PRESET_STORAGE_KEY, JSON.stringify(preset))
}
