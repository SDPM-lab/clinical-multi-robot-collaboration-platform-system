export const OVERVIEW_CAMERA_PRESET_STORAGE_KEY = 'hospital-rmf-overview-camera-preset'

export const DEFAULT_OVERVIEW_CAMERA_PRESET = Object.freeze({
  position: Object.freeze([
     0.14390273296084735,
     13.475785222949447,
     28.307966519227403
  ]),
  target: Object.freeze([
    0.23916773629652,
    -1.3505984527272599,
    1.790555498496682
  ]),
  zoom: 1,
  quaternion: Object.freeze([
    -0.2521552555293638,
    -0.0017382207696028773,
    -0.00045293814190487756,
    0.9676851246890783
  ]),
  positionOffset: Object.freeze([
    0.14390273296084735,
    12.619168799728499,
    28.307966519227403
  ]),
  targetOffset: Object.freeze([
    0.23916773629652,
    -2.2072148759482078,
    1.790555498496682
  ]),
})

const isVector = (value, length) => (
  Array.isArray(value)
  && value.length === length
  && value.every(Number.isFinite)
)

export function isOverviewCameraPreset(value) {
  return Boolean(
    value
    && isVector(value.positionOffset, 3)
    && isVector(value.targetOffset, 3)
    && Number.isFinite(value.zoom)
    && value.zoom > 0,
  )
}

export function readStoredOverviewCameraPreset() {
  try {
    const value = JSON.parse(localStorage.getItem(OVERVIEW_CAMERA_PRESET_STORAGE_KEY))
    return isOverviewCameraPreset(value) ? value : null
  } catch {
    return null
  }
}

export function storeOverviewCameraPreset(preset) {
  localStorage.setItem(OVERVIEW_CAMERA_PRESET_STORAGE_KEY, JSON.stringify(preset))
}
