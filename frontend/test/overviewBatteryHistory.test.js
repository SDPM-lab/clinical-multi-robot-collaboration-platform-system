import { effectScope, nextTick, ref } from 'vue'
import { expect, it } from 'vitest'
import { useOverviewBatteryHistory } from '@/composables/useOverviewBatteryHistory.js'
it('bounds telemetry, isolates floors, deduplicates unrelated updates, and stops on scope disposal', async () => {
  const scope = effectScope()
  const status = ref({ floor1: { R01: { robotId: 'R01', battery: 82, updatedAt: 't0' } } })
  const history = scope.run(() => useOverviewBatteryHistory(status))
  for (let i = 1; i < 36; i++) {
    status.value.floor1.R01.updatedAt = `t${i}`
    await nextTick()
  }
  expect(history.floor1.R01).toHaveLength(30)
  status.value.floor1.R01.currentTask = 'changed'
  await nextTick()
  expect(history.floor1.R01).toHaveLength(30)
  status.value = { floor2: { R01: { robotId: 'R01', battery: 71, updatedAt: 't36' } } }
  await nextTick()
  expect(history.floor2.R01[0].value).toBe(71)
  expect(history.floor1.R01.at(-1).value).toBe(82)
  scope.stop()
  status.value.floor2.R01.battery = 60
  await nextTick()
  expect(history.floor2.R01).toHaveLength(1)
})
