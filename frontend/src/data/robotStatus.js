export const robotStateColors = Object.freeze({
  idle: '#6F9B7B',
  busy: '#C96F3B',
  charging: '#4F9F91',
  offline: '#898E8B',
  error: '#C96561',
})

export const robotStateLabels = Object.freeze({
  idle: '待命',
  busy: '忙碌',
  charging: '充電中',
  offline: '離線',
  error: '異常',
})

export function getBatteryColor(battery) {
  if (battery <= 20) return '#C96561'
  if (battery <= 40) return '#C59A52'
  return '#6F9B7B'
}
