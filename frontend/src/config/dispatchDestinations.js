// Labels are for display only; form and API values are stable waypoint IDs.
export const dispatchWaypointLabels = Object.freeze({
  reception_back: 'Nurse Reception',
  nurse_station: 'Nurse Station',
  pharmacy: 'Pharmacy',
  consult_2_1: 'Consultation Room 2',
  ward_a_1: 'Ward A',
  ward_a_2: 'Ward A',
  charging_station_1: 'Charging Station A',
  charging_station_2: 'Charging Station B',
  lab: 'Laboratory',
  pantry: 'Pantry',
  consult_1_2: 'Consultation Room 1',
  consult_2_2: 'Consultation Room 2',
  consult_3_2: 'Consultation Room 3',
  ward_b_2: 'Ward B',
  blood_draw: 'Blood Draw',
  'x-ray': 'X-Ray',
  ultrasound_2: 'Ultrasound',
  ecg_2: 'ECG',
  therapy_room: 'Therapy Room',
  waste_return_2: 'Waste Return',
  clothes_return_2: 'Clothes Return',
})

// Keep this order aligned with experiments/fleet_sizing/rl/observation.py LOCATIONS.
export const PPO_TASK_WAYPOINT_IDS = Object.freeze([
  'charging_station_2',
  'ward_a_2',
  'ward_b_2',
  'consult_1_2',
  'consult_2_2',
  'consult_3_2',
  'nurse_station',
  'blood_draw',
  'x-ray',
  'ultrasound_2',
  'ecg_2',
  'therapy_room',
  'waste_return_2',
  'clothes_return_2',
  'pharmacy',
  'lab',
])

export const dispatchTaskLocations = Object.freeze([...new Set(PPO_TASK_WAYPOINT_IDS.map(id => dispatchWaypointLabels[id]))])
