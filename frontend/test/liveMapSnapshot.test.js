import { expect,it } from 'vitest'
import { adaptLiveMapSnapshot,orderLiveMapRobots,buildLiveMapRoutes,buildLiveMapLocationDetails,withPreviewPositions,placeSimulatedRobotsAtRouteStart } from '@/data/liveMapSnapshot.js'
const snapshot={robots:[{id:'robot-a',name:'機器人 A',levelName:'L1',status:'已指派待執行',hasTelemetry:true,x:0,y:0,yaw:0,battery:80},{id:'robot-b',name:'機器人 B',hasTelemetry:false,status:'離線',levelName:'',battery:0}]}
it('keeps canonical robot and task IDs and does not turn assignment into running',()=>{
 const result=adaptLiveMapSnapshot(snapshot,[{id:'uuid',taskCode:'T0008',taskType:'medication_delivery',source:'pharmacy',destination:'lab',status:'assigned',assignedRobot:'robot-a',scheduledAt:'2026-11-08T10:00:00+08:00',priority:'normal'}])
 expect(result.robots[0]).toMatchObject({id:'robot-a',floorId:'floor1',hasPose:true,state:'assigned'})
 expect(result.robots[0].displayCode).toBe('C01')
 expect(result.robots[1]).toMatchObject({floorId:null,hasPose:false,battery:null})
 expect(result.tasks[0]).toMatchObject({id:'uuid',taskCode:'T0008',robotId:'robot-a',status:'assigned',backendDestination:'lab'})
 expect(result.tasks[0]).toMatchObject({source:'pharmacy',destination:'lab'})
})
it('builds a route from raw backend waypoint IDs after adapting a running task',()=>{
 const data={vertices:[{id:'v1'},{id:'v2'},{id:'v3'}],namedWaypoints:[{id:'v1',name:'pharmacy'},{id:'v3',name:'ward_a_2'}],lanes:[{from:'v1',to:'v2'},{from:'v2',to:'v3'}]}
 const {tasks}=adaptLiveMapSnapshot(snapshot,[{id:'running-id',taskCode:'T0009',taskType:'medication_delivery',source:'pharmacy',destination:'ward_a_2',status:'running',assignedRobot:'robot-a',scheduledAt:'2026-11-08T10:00:00+08:00',priority:'normal'}])
 expect(buildLiveMapRoutes(data,tasks)[0].vertexIds).toEqual(['v1','v2','v3'])
})
it('builds graph reference routes for new backend tasks beyond the three demos',()=>{
 const data={vertices:[{id:'v1'},{id:'v2'},{id:'v3'}],namedWaypoints:[{id:'v1',name:'ultrasound'},{id:'v3',name:'ecg'}],lanes:[{from:'v1',to:'v2'},{from:'v2',to:'v3'}]}
 const task={id:'uuid-new',taskCode:'T0100',robotId:'robot-hospital_robot_7',source:'ultrasound',backendDestination:'ecg',status:'executing',priority:'high'}
 expect(buildLiveMapRoutes(data,[task])[0]).toMatchObject({id:'uuid-new',vertexIds:['v1','v2','v3'],progress:0})
 const details=buildLiveMapLocationDetails(data,[task],[])
 expect(details.ecg).toMatchObject({taskId:'uuid-new',taskCode:'T0100',robotId:'robot-hospital_robot_7'})
 expect(buildLiveMapRoutes(data,[{...task,status:'assigned'}])).toEqual([])
})

it('keeps seven preview positions stable and replaces them with actual telemetry',()=>{
 const data={vertices:Array.from({length:12},(_,index)=>({id:`v${index}`,name:`junction_${index}`,x:index*3,y:2})),lanes:Array.from({length:11},(_,index)=>({from:`v${index}`,to:`v${index+1}`}))}
 const robots=Array.from({length:7},(_,index)=>({id:`robot-${index}`,floorId:'floor1',hasPose:false,hasTelemetry:false}))
 const placements=new Map()
 const first=withPreviewPositions(robots,data,placements,()=>0.3)
 expect(new Set(first.map(robot=>robot.x)).size).toBe(7)
 expect(first.every(robot=>robot.positionSource==='preview')).toBe(true)
 expect(robots.every(robot=>!robot.hasPose && robot.x===undefined)).toBe(true)
 const second=withPreviewPositions(robots,data,placements,()=>0.9)
 expect(second.map(robot=>robot.x)).toEqual(first.map(robot=>robot.x))
 const actual=withPreviewPositions([{...robots[0],hasPose:true,hasTelemetry:true,x:99,y:15,yaw:1}],data,placements)
 expect(actual[0].x).toBe(99)
 expect(actual[0].positionSource).toBeUndefined()
})

it('places only development preview models at the simulated route source',()=>{
 const data={vertices:[{id:'v1',x:4,y:6},{id:'v2',x:8,y:6}]}
 const route={robotId:'robot-a',isSimulated:true,vertexIds:['v1','v2']}
 const preview={id:'robot-a',positionSource:'preview',x:10,y:20}
 expect(placeSimulatedRobotsAtRouteStart([preview],[route],data)[0]).toMatchObject({x:4,y:6,yaw:0})
 const actual={id:'robot-a',hasPose:true,x:12,y:15}
 expect(placeSimulatedRobotsAtRouteStart([actual],[route],data)[0]).toBe(actual)
})

it('orders working and assigned robots before idle robots without mutating the roster', () => {
 const robots = [
  {id:'C01',state:'idle'}, {id:'W01',state:'assigned'}, {id:'C02',state:'idle'},
  {id:'W02',state:'busy'}, {id:'W03',state:'assigned'},
 ]
 expect(orderLiveMapRobots(robots).map(robot => robot.id)).toEqual(['W02','W01','W03','C01','C02'])
 expect(robots.map(robot => robot.id)).toEqual(['C01','W01','C02','W02','W03'])
})
