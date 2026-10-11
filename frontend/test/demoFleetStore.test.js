import { describe, expect, it } from 'vitest'
import { demoFleetStore, secondsToTime, timeToSeconds } from '../src/stores/demoFleetStore.js'

describe('demo fleet store scheduling rules', () => {
  it('round-trips second-precision times', () => {
    expect(timeToSeconds('10:05:30')).toBe(36330)
    expect(secondsToTime(36330 + 720)).toBe('10:17:30')
  })

  it('rejects overlaps and insufficient battery', () => {
    expect(demoFleetStore.validateTask({ robotId: 'R01', title: '巡檢', origin: 'Pharmacy', destination: 'Laboratory', startTime: '09:35:00', endTime: '09:40:00' }).ok).toBe(false)
    expect(demoFleetStore.validateTask({ robotId: 'R03', title: '巡檢', origin: 'Pharmacy', destination: 'Laboratory', startTime: '12:00:00', endTime: '12:10:00' }).reason).toContain('電量不足')
  })

  it('allows the same time on another date while preserving same-day conflicts', () => {
    const task = { robotId: 'R01', title: '巡檢', origin: 'Pharmacy', destination: 'Laboratory', startTime: '09:35:00', endTime: '09:40:00' }
    expect(demoFleetStore.validateTask({ ...task, date: '2026-08-31' }).ok).toBe(false)
    expect(demoFleetStore.validateTask({ ...task, robotId: 'R02', date: '2026-08-31' }).ok).toBe(true)
    expect(demoFleetStore.validateTask({ ...task, date: '2026-09-02' }).ok).toBe(true)
  })

  it('accepts newly exposed TE room stations but rejects visual-only rooms', () => {
    const task = { robotId: 'R02', title: '檢體運送', origin: 'Blood Draw', destination: 'Ward B', startTime: '12:00:00', endTime: '12:12:00' }
    expect(demoFleetStore.validateTask(task).ok).toBe(true)
    expect(demoFleetStore.validateTask({ ...task, destination: 'Director' }).ok).toBe(false)
  })

  it('rejects duplicate IDs, duplicate namespaces, Graph 1, and invalid battery values', () => {
    const base = {
      id: 'R04', name: 'Robot 04', rosNamespace: '/robot_04', navGraphIndex: 0,
      chargingWaypoint: 'charging_station_1', battery: 80, maxSpeedMps: 0.7, maxPayloadKg: 20,
    }
    expect(demoFleetStore.validateRobot({ ...base, id: 'R01' }).reason).toContain('已存在')
    expect(demoFleetStore.validateRobot({ ...base, rosNamespace: '/robot_02' }).reason).toContain('已被使用')
    expect(demoFleetStore.validateRobot({ ...base, rosNamespace: 'robot_02/' }).reason).toContain('已被使用')
    expect(demoFleetStore.validateRobot({ ...base, navGraphIndex: 1 }).reason).toContain('不允許')
    expect(demoFleetStore.validateRobot({ ...base, battery: 101 }).reason).toContain('0～100')
  })

  it('atomically rejects a conflicting batch without changing task times', () => {
    const task = demoFleetStore.tasks.value.find((entry) => entry.id === 'T006')
    const original = task.startTime
    const result = demoFleetStore.moveTasks([{ taskId: 'T006', startSeconds: timeToSeconds('14:25:00') }])
    expect(result.ok).toBe(false)
    expect(result.reason).toContain('時間重疊')
    expect(task.startTime).toBe(original)
  })

  it('removes a task and clears its robot queue entry', () => {
    const robot = demoFleetStore.robots.value.find((entry) => entry.id === 'R02')
    const queuedBefore = robot.queuedTasks
    const created = demoFleetStore.createTask({ robotId:'R02', title:'檢體運送', type:'檢體運送', origin:'Pharmacy', destination:'Laboratory', date:'2026-10-01', startTime:'08:00:00', durationSeconds:720, priority:'normal', notes:'' })
    expect(created.ok).toBe(true)
    expect(robot.queuedTaskIds).toContain(created.task.id)
    expect(demoFleetStore.deleteTask(created.task.id).ok).toBe(true)
    expect(demoFleetStore.tasks.value.some((task) => task.id === created.task.id)).toBe(false)
    expect(robot.queuedTaskIds).not.toContain(created.task.id)
    expect(robot.queuedTasks).toBe(queuedBefore)
  })
})
