export const overviewDemoData = Object.freeze({
  mode: 'demo',
  tasks: Object.freeze({
    completed: 18,
    inProgress: 1,
    waiting: 2,
    completionHistory: Object.freeze([68, 72, 70, 77, 81, 83, 86]),
  }),
  fleet: Object.freeze({
    online: 3,
    total: 3,
    activeTasks: 1,
    charging: 1,
  }),
  system: Object.freeze({
    connected: true,
    critical: 0,
    warning: 1,
    source: '展示資料',
  }),
  robots: Object.freeze([
    Object.freeze({ id: 'R01', name: 'C01', state: 'busy', battery: 82, queuedTasks: 2 }),
    Object.freeze({ id: 'R02', name: 'C02', state: 'charging', battery: 34, queuedTasks: 0 }),
    Object.freeze({ id: 'R03', name: 'M01', state: 'idle', battery: 18, queuedTasks: 1 }),
  ]),
})

export function getTaskCompletion(tasks) {
  const total = tasks.completed + tasks.inProgress + tasks.waiting
  return total > 0 ? Math.round((tasks.completed / total) * 100) : 0
}

export function getAverageBattery(robots) {
  if (robots.length === 0) return 0
  return Math.round(robots.reduce((sum, robot) => sum + robot.battery, 0) / robots.length)
}
