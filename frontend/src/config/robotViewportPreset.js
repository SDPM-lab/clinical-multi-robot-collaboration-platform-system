export const ROBOT_CAMERA_PRESET_KEY = 'hospital-rmf-robot-camera-v1'
export const ROBOT_MODEL_PRESET_KEY = 'hospital-rmf-robot-model-v1'

export const defaultRobotModelPreset = () => ({ position: { x: 0, y: 0, z: 0 }, rotationY: 0, scale: 1 })

const finiteVector = value => value && ['x', 'y', 'z'].every(key => Number.isFinite(Number(value[key])))
export const validRobotCameraPreset = value => Boolean(
  value && finiteVector(value.position) && finiteVector(value.target)
  && Number.isFinite(Number(value.fov)) && Number(value.fov) >= 20 && Number(value.fov) <= 70
  && (value.aspect == null || (Number.isFinite(Number(value.aspect)) && Number(value.aspect) >= .2 && Number(value.aspect) <= 5))
  && Math.hypot(...['x', 'y', 'z'].map(key => Number(value.position[key]) - Number(value.target[key]))) > .1,
)
export const validRobotModelPreset = value => Boolean(
  value && finiteVector(value.position) && Number.isFinite(Number(value.rotationY))
  && Number.isFinite(Number(value.scale)) && Number(value.scale) >= .5 && Number(value.scale) <= 2,
)

const read = (key, validate) => {
  try { const value = JSON.parse(localStorage.getItem(key) || 'null'); return validate(value) ? value : null }
  catch { return null }
}
export const readRobotCameraPreset = () => read(ROBOT_CAMERA_PRESET_KEY, validRobotCameraPreset)
export const readRobotModelPreset = () => read(ROBOT_MODEL_PRESET_KEY, validRobotModelPreset)
export const storeRobotCameraPreset = value => { if (validRobotCameraPreset(value)) localStorage.setItem(ROBOT_CAMERA_PRESET_KEY, JSON.stringify(value)) }
export const storeRobotModelPreset = value => { if (validRobotModelPreset(value)) localStorage.setItem(ROBOT_MODEL_PRESET_KEY, JSON.stringify(value)) }
