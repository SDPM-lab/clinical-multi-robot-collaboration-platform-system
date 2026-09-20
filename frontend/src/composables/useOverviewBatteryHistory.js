import { reactive, watch } from 'vue'

// Owned by the Overview scope: Vue stops the watcher when the page unmounts.
export function useOverviewBatteryHistory(status) {
  const history = reactive({ floor1: {}, floor2: {}, floor3: {} })
  watch(status, floors => {
    for (const [floor, robots] of Object.entries(floors)) {
      for (const robot of Object.values(robots)) {
        if (!Number.isFinite(robot.battery)) continue
        const points = history[floor][robot.robotId] ||= []
        const last = points.at(-1)
        const value = Math.max(0, Math.min(100, robot.battery))
        if (last?.value === value && last?.updatedAt === robot.updatedAt) continue
        points.push({ value, updatedAt: robot.updatedAt, timestamp: Number.isFinite(Date.parse(robot.updatedAt)) ? Date.parse(robot.updatedAt) : Date.now(), status: robot.status, task: robot.currentTask, taskId: robot.taskId, time: robot.updatedAt ? robot.updatedAt.slice(11, 16) : new Date().toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit' }) })
        if (points.length > 30) points.splice(0, points.length - 30)
      }
    }
  }, { immediate: true, deep: true })
  return history
}
