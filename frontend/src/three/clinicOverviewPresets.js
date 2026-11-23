export const OVERVIEW_CAMERA_PRESET_STORAGE_KEY = 'overview-camera-preset-v9'
export const OVERVIEW_MODEL_PRESET_STORAGE_KEY = 'overview-model-preset-v4'

export const DEFAULT_OVERVIEW_CAMERA_PRESET = Object.freeze({
  position: Object.freeze({ x: 28.068, y: 15.9581, z: 52.631 }),
  target: Object.freeze({ x: -0.6117, y: 6.0941, z: 2.5053 }),
})

export const DEFAULT_OVERVIEW_MODEL_PRESET = Object.freeze({
  position: Object.freeze({ x: -2.6711178700891924, y: 3.9159005573132415, z: -0.0891364507224327 }),
  rotation: Object.freeze({ x: 0, y: 0.40120019531249995, z: 0 }),
  scale: 0.8951884436412747,
})

const finiteVector = (value) => value && ['x', 'y', 'z'].every((key) => Number.isFinite(Number(value[key])))

export const isOverviewCameraPreset = (value) => Boolean(
  value && finiteVector(value.position) && finiteVector(value.target),
)

export const isOverviewModelPreset = (value) => Boolean(
  value && finiteVector(value.position) && finiteVector(value.rotation)
  && Number.isFinite(Number(value.scale)) && Number(value.scale) > 0,
)

const readPreset = (key, validator) => {
  try {
    const value = JSON.parse(localStorage.getItem(key) || 'null')
    return validator(value) ? value : null
  } catch {
    return null
  }
}

export const readOverviewCameraPreset = () => readPreset(OVERVIEW_CAMERA_PRESET_STORAGE_KEY, isOverviewCameraPreset)
export const readOverviewModelPreset = () => readPreset(OVERVIEW_MODEL_PRESET_STORAGE_KEY, isOverviewModelPreset)

export const storeOverviewCameraPreset = (preset) => {
  if (isOverviewCameraPreset(preset)) localStorage.setItem(OVERVIEW_CAMERA_PRESET_STORAGE_KEY, JSON.stringify(preset))
}

export const storeOverviewModelPreset = (preset) => {
  if (isOverviewModelPreset(preset)) localStorage.setItem(OVERVIEW_MODEL_PRESET_STORAGE_KEY, JSON.stringify(preset))
}

export const clearOverviewCameraPreset = () => localStorage.removeItem(OVERVIEW_CAMERA_PRESET_STORAGE_KEY)
export const clearOverviewModelPreset = () => localStorage.removeItem(OVERVIEW_MODEL_PRESET_STORAGE_KEY)

export const cloneDefaultOverviewModelPreset = () => ({
  position: { ...DEFAULT_OVERVIEW_MODEL_PRESET.position },
  rotation: { ...DEFAULT_OVERVIEW_MODEL_PRESET.rotation },
  scale: DEFAULT_OVERVIEW_MODEL_PRESET.scale,
})

export const cloneDefaultOverviewCameraPreset = () => ({
  position: { ...DEFAULT_OVERVIEW_CAMERA_PRESET.position },
  target: { ...DEFAULT_OVERVIEW_CAMERA_PRESET.target },
})
