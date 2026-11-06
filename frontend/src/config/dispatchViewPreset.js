export const DISPATCH_CAMERA_PRESET_KEY = 'hospital-rmf-dispatch-camera-v1'
export const DISPATCH_MODEL_PRESET_KEY = 'hospital-rmf-dispatch-model-v1'

export const defaultDispatchModelPreset = () => ({ position: { x: 0, y: 0, z: 0 }, rotationY: 0, scale: 1 })

const finiteVector = (value) => value && ['x', 'y', 'z'].every((key) => Number.isFinite(Number(value[key])))
export const validDispatchCameraPreset = (value) => Boolean(
  value && finiteVector(value.position) && finiteVector(value.target)
  && Number.isFinite(Number(value.zoom)) && Number(value.zoom) >= .45 && Number(value.zoom) <= 5,
)
export const validDispatchModelPreset = (value) => Boolean(
  value && finiteVector(value.position) && Number.isFinite(Number(value.rotationY))
  && Number.isFinite(Number(value.scale)) && Number(value.scale) >= .5 && Number(value.scale) <= 2,
)
const read = (key, validate) => {
  try { const value = JSON.parse(localStorage.getItem(key) || 'null'); return validate(value) ? value : null }
  catch { return null }
}
export const readDispatchCameraPreset = () => read(DISPATCH_CAMERA_PRESET_KEY, validDispatchCameraPreset)
export const readDispatchModelPreset = () => read(DISPATCH_MODEL_PRESET_KEY, validDispatchModelPreset)
export const storeDispatchCameraPreset = (value) => { if (validDispatchCameraPreset(value)) localStorage.setItem(DISPATCH_CAMERA_PRESET_KEY, JSON.stringify(value)) }
export const storeDispatchModelPreset = (value) => { if (validDispatchModelPreset(value)) localStorage.setItem(DISPATCH_MODEL_PRESET_KEY, JSON.stringify(value)) }
