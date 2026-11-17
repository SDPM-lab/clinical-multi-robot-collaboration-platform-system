import { computed } from 'vue'
import { taskApi } from '@/services/taskApi.js'
import { adaptBackendHistoryTasks } from './scheduleHistory.js'

// Wait for real API data; an empty result remains empty without demo fallback.
export async function createHistorySource() {
  const [tasks, robots] = await Promise.allSettled([taskApi.getTaskRecords(), taskApi.getRobots()])
  if (tasks.status === 'rejected') throw tasks.reason
  // Robot names are optional enrichment; recorded robot IDs remain usable.
  const robotList = robots.status === 'fulfilled' ? robots.value : []
  const events = adaptBackendHistoryTasks(tasks.value, robotList)
  return computed(() => ({ events, robots: robotList, demo: false, error: '', robotLookupFailed: robots.status === 'rejected' }))
}
