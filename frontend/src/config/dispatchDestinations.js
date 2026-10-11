// These are reviewed Graph 0 room stations. Corridor junctions stay routable
// without appearing as task destinations. The labels are unique form values.
export const dispatchWaypointLabels = Object.freeze({
  reception_back: 'Nurse Reception',
  nurse_station: 'Nurse Station',
  pharmacy: 'Pharmacy',
  consult_2_1: 'Consultation Room 2',
  ward_a_1: 'Ward A',
  charging_station_1: 'Charging Station A',
  lab: 'Laboratory',
  pantry: 'Pantry',
  consult_1_2: 'Consultation Room 1',
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

export const dispatchTaskLocations = Object.freeze(Object.values(dispatchWaypointLabels))
