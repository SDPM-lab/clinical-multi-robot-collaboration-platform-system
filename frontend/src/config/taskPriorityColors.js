export const taskPriorityColors = Object.freeze({
  low: '#E0BD45',
  normal: '#FB9966',
  high: '#D65B57',
  emergency: '#954D43',
})

export const taskPriorityColor = priority => taskPriorityColors[priority === 'urgent' ? 'emergency' : priority] || taskPriorityColors.normal
