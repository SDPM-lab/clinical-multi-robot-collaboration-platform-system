import { rmfToThree, rmfMapTransform } from './rmfMapTransform.js'

export const dispatchFloors = Object.freeze([
  { id: 1, label: 'F1' },
  { id: 2, label: 'F2' },
  { id: 3, label: 'F3' },
])
// Explicit semantic links only. Model connector meshes are visual geometry,
// never a source of navigable edges or directions.
export const dispatchLocations = Object.freeze({
  reception_back: { room: 'reception_desk', connector: 'reception_door__reception_desk_edge' },
  nurse_station: { room: 'nurse_station', connector: 'nurse_door__nurse_station_edge' },
  pharmacy: { room: 'pharmacy', connector: 'pharmacy_door__pharmacy_edge' },
  consult_2_1: { room: 'consult_2', connector: 'consult_2_door__consult_2_edge' },
  ward_a_1: { room: 'ward_a', connector: 'ward_a_door__ward_a_edge' },
  charging_station_1: { room: 'charging', connector: 'charge_door__charging_edge' },
  lab: { room: 'laboratory', connector: 'lab_door__laboratory_edge' },
  pantry: { room: 'pantry', connector: 'pantry_door__pantry_edge' },
  consult_1_2: { room: 'consult_1' },
  consult_3_2: { room: 'consult_3' },
  ward_b_2: { room: 'ward_b' },
  blood_draw: { room: 'blood_draw' },
  'x-ray': { room: 'xray' },
  ultrasound_2: { room: 'ultrasound' },
  ecg_2: { room: 'ecg' },
  therapy_room: { room: 'therapy' },
  waste_return_2: { room: 'waste_return' },
  clothes_return_2: { room: 'clothes_return' },
})

// Start with the existing Traffic Editor -> hospital transform as an explicitly
// uncalibrated preview. User adjustments are local presentation settings only.
export const dispatchRmfTransform = Object.freeze({ ...rmfMapTransform, floorY: .14 })
export const alignmentStorageKey = 'hospital-rmf-dispatch-alignment-v1'
export function validDispatchTransform(value) {
  return value && ['scale', 'rotation', 'offsetX', 'offsetZ', 'floorY'].every((key) => Number.isFinite(value[key]))
    && value.scale >= .05 && value.scale <= 20 && typeof value.invertX === 'boolean' && typeof value.invertY === 'boolean'
}
export function rmfToDispatch(point, transform = dispatchRmfTransform) {
  if (!validDispatchTransform(transform) || !Number.isFinite(point?.x) || !Number.isFinite(point?.y) || point.level !== 'L1') return null
  return rmfToThree(point, transform)
}

export function modelObjectName(object) {
  return (object.userData?.name || object.name || '').replace(/\.\d+$/, '')
}
export function isDispatchPreview(object) {
  return object.isCamera || object.isLight || /^Preview_Ground_NOT_FOR_EXPORT(?:\.?\d+)?$/.test(object.userData?.name || object.name || '')
}
