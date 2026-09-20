export const taskTypeColors = Object.freeze({
  medicine: Object.freeze({ main: '#C96F3B', soft: 'rgba(201, 111, 59, 0.12)' }),
  specimen: Object.freeze({ main: '#4F8FD8', soft: '#C8DDF4' }),
  supplies: Object.freeze({ main: '#8C72D8', soft: '#DCD2F5' }),
  waste: Object.freeze({ main: '#C96561', soft: 'rgba(201, 101, 97, 0.15)' }),
  document: Object.freeze({ main: '#C59A52', soft: 'rgba(197, 154, 82, 0.15)' }),
  inspection: Object.freeze({ main: '#4F9F91', soft: 'rgba(79, 159, 145, 0.15)' }),
  charging: Object.freeze({ main: '#6F9B7B', soft: 'rgba(111, 155, 123, 0.15)' }),
})

const taskTypeByLabel = Object.freeze({
  藥品配送: 'medicine',
  檢體運送: 'specimen',
  病房物資補充: 'supplies',
  醫療廢棄物運送: 'waste',
  文件配送: 'document',
  巡檢: 'inspection',
  前往充電: 'charging',
})

export const getTaskTypeKey = (task) => taskTypeByLabel[task.type || task.title] || 'document'
export const getTaskTypeColor = (task) => taskTypeColors[getTaskTypeKey(task)]
