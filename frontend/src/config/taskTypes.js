// Keep these values aligned with backend/Server/Models/TaskType.cs.
export const TASK_TYPE_BY_LABEL = Object.freeze({
  藥品配送: 'medication_delivery',
  檢體配送: 'specimen_delivery',
  廢棄物運送: 'waste_transport',
  衣物回收: 'clothes_collection',
  病房服務: 'ward_service',
})

export const TASK_TYPE_LABELS = Object.freeze(Object.keys(TASK_TYPE_BY_LABEL))

// Mirrors TaskService.GetRequiredCapabilities on the backend.
export const REQUIRED_CAPABILITIES_BY_TASK_TYPE = Object.freeze(Object.fromEntries(
  Object.values(TASK_TYPE_BY_LABEL).map(type => [type, Object.freeze([type])]),
))

const commonSources = ['ward_a_2','ward_b_2','consult_1_2','consult_2_2','consult_3_2']
export const TASK_LOCATION_IDS = Object.freeze({
  waste_transport: Object.freeze({ sources: [...commonSources,'nurse_station','blood_draw','x-ray','ultrasound_2','ecg_2','therapy_room'], destinations: ['waste_return_2'] }),
  clothes_collection: Object.freeze({ sources: ['ward_a_2','ward_b_2','x-ray','ultrasound_2','ecg_2','therapy_room'], destinations: ['clothes_return_2'] }),
  medication_delivery: Object.freeze({ sources: ['pharmacy'], destinations: [...commonSources,'nurse_station'] }),
  specimen_delivery: Object.freeze({ sources: [...commonSources,'blood_draw'], destinations: ['lab'] }),
  ward_service: Object.freeze({ sources: ['nurse_station'], destinations: ['ward_a_2','ward_b_2'] }),
})
