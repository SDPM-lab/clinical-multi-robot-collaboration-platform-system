// Keep these values aligned with backend/Server/Models/TaskType.cs.
export const TASK_TYPE_BY_LABEL = Object.freeze({
  藥品配送: 'MedicineDelivery',
  檢體配送: 'SpecimenDelivery',
  一般配送: 'GeneralDelivery',
  廢棄物收集: 'WasteCollection',
})

export const TASK_TYPE_LABELS = Object.freeze(Object.keys(TASK_TYPE_BY_LABEL))

// Mirrors TaskService.GetRequiredCapabilities on the backend.
export const REQUIRED_CAPABILITIES_BY_TASK_TYPE = Object.freeze({
  MedicineDelivery: Object.freeze(['Navigation', 'MedicineDelivery']),
  SpecimenDelivery: Object.freeze(['Navigation', 'SpecimenDelivery']),
  GeneralDelivery: Object.freeze(['Navigation', 'GeneralDelivery']),
  WasteCollection: Object.freeze(['Navigation', 'GeneralDelivery']),
})
