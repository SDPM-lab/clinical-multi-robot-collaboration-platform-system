export const BAYMAX_MODEL_URL = '/models/baymax_nurse.glb'
export const ACTOR_FORWARD_AXIS_OFFSET = -Math.PI / 2

export const baymaxConfig = Object.freeze({
  targetHeight: 1.65,
  displayScaleMultiplier: 0.8,
  floorY: 0,
  speed: 0.65,
  forwardAxisOffset: ACTOR_FORWARD_AXIS_OFFSET,
  turnSpeed: 9,
})

export const actorVisibility = Object.freeze({
  overview: true,
  realtimeMap: true,
})
