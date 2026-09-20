import { describe, it, expect } from 'vitest'
import { buildingBatteryHistory, createFloorRobotStatus } from '@/data/overviewStatusData.js'
const robots = [{id:'R01',battery:82,state:'executing',activeTaskId:'T1'},{id:'R02',battery:34,state:'charging'},{id:'R03',battery:18,state:'idle'}]
describe('Overview floor state', () => {
  it('scopes demo robots and never assigns tasks or battery to an absent robot', () => {
    const result = createFloorRobotStatus(robots,[{id:'T1',title:'配送'}],true)
    expect(result.floor1.R01.currentTask).toBe('配送')
    expect(result.floor2.R01).toMatchObject({status:'absent',battery:null,currentTask:null,pendingTaskCount:null})
    expect(result.floor2.R02.battery).toBe(34)
    expect(result.floor3.R03.battery).toBe(18)
  })
  it('prioritizes supplied floor telemetry and does not invent location when not in demo', () => {
    const result = createFloorRobotStatus([{...robots[0],floorId:'floor3',battery:79}],[],true)
    expect(result.floor3.R01.battery).toBe(79)
    expect(result.floor1.R01.status).toBe('absent')
    expect(createFloorRobotStatus(robots).floor1.R01.status).toBe('unknown')
  })
  it('has distinct deterministic hourly history for each floor', () => {
    expect(buildingBatteryHistory.floor1).toHaveLength(5)
    expect(buildingBatteryHistory.floor1).not.toEqual(buildingBatteryHistory.floor2)
    expect(buildingBatteryHistory.floor1[4].batteries.R01).toBe(82)
  })
})
