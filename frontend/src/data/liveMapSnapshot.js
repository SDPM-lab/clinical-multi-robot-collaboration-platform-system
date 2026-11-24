import { toScheduleTask } from '@/services/taskApi.js'
import { normalizeFloor } from '@/data/overviewStatusData.js'
import { dispatchWaypointLabels } from '@/config/dispatchDestinations.js'
import { robotDisplayCode } from '@/config/robotDisplayCode.js'
import { shortestVertexPath, robotRouteColors, priorityOrder } from '@/data/demoActiveRoutes.js'

const states = { '待命':'idle','待命中':'idle','在線':'idle','忙碌':'busy','已指派待執行':'assigned','執行任務中':'busy','充電中':'charging','緊急停止':'error','暫停':'paused','離線':'offline' }
export function adaptLiveMapSnapshot(snapshot, records) {
  const robots = snapshot.robots.map(robot => ({ ...robot, displayCode:robotDisplayCode(robot.id),
    floorId:normalizeFloor(robot.levelName), state:states[robot.status] || 'unknown',
    battery:robot.hasTelemetry ? robot.battery : null,
    hasPose:robot.hasTelemetry === true && !!normalizeFloor(robot.levelName) && [robot.x,robot.y,robot.yaw].every(Number.isFinite),
  }))
  const tasks = records.map(record => ({ ...toScheduleTask(record), source:record.source, destination:record.destination,
    backendStatus:record.status, backendDestination:record.destination,
    status:record.status === 'running' ? 'executing' : record.status,
  }))
  return {robots,tasks,connection:snapshot.connection}
}

const robotDrawerRank = { busy: 0, assigned: 1 }

export function orderLiveMapRobots(robots) {
  return [...robots].sort((a, b) => (robotDrawerRank[a.state] ?? 2) - (robotDrawerRank[b.state] ?? 2))
}

// Traffic Editor supplies the graph; this is a reference route, not an execution trace.
export function buildLiveMapRoutes(data,tasks) {
  const waypointByName = new Map(data.namedWaypoints.map(point => [point.name,point]))
  return tasks.filter(task=>task.status==='executing' && task.robotId).map(task=>{
    const source=waypointByName.get(task.source),destination=waypointByName.get(task.destinationId || task.backendDestination)
    const vertexIds=source && destination ? shortestVertexPath(data,source.id,destination.id) : []
    return {...task,taskId:task.id,vertexIds,progress:0,colors:robotRouteColors[task.robotId] || robotRouteColors.R04}
  }).filter(route=>route.vertexIds.length>1)
}
export function buildLiveMapLocationDetails(data,tasks,robots) {
  const endpoints = new Set(tasks.flatMap(task=>[task.source,task.backendDestination]))
  const details=Object.fromEntries(data.namedWaypoints.filter(point=>dispatchWaypointLabels[point.name] || endpoints.has(point.name)).map(point=>[point.name,{label:dispatchWaypointLabels[point.name] || point.name, ...(point.name.startsWith('charging_station_') ? {statusKey:'charging'} : {})}]))
  const ordered=[...tasks].filter(task=>task.status==='executing').sort((a,b)=>(priorityOrder[a.priority]??2)-(priorityOrder[b.priority]??2))
  for(const task of ordered) for(const name of [task.source,task.backendDestination]) {
    const detail=details[name]
    if(!detail || detail.taskId) continue
    Object.assign(detail,{taskId:task.id,taskCode:task.taskCode || task.id,robotId:task.robotId,
      robot:robotDisplayCode(task.robotId),priority:task.priority,
      statusKey:'active',color:(robotRouteColors[task.robotId] || robotRouteColors.R04).main,
      isDestination:name===task.backendDestination})
  }
  return details
}

// Session-local preview placement; never writes simulated telemetry to the backend.
export function withPreviewPositions(robots,data,placements,random=Math.random) {
  const connected=new Set(data.lanes.flatMap(lane=>[lane.from,lane.to]))
  const vertices=data.vertices.filter(vertex=>connected.has(vertex.id) && Number.isFinite(vertex.x) && Number.isFinite(vertex.y))
  const junctions=vertices.filter(vertex=>/junction/.test(vertex.name || ''))
  const candidates=junctions.length>=robots.length ? junctions : vertices
  const occupied=robots.filter(robot=>robot.hasPose).map(robot=>({x:robot.x,y:robot.y}))
  return robots.map(robot=>{
    if(robot.hasPose || robot.floorId!=='floor1') return robot
    let position=placements.get(robot.id)
    if(!position){
      const used=[...placements.values(),...occupied]
      const available=candidates.filter(vertex=>used.every(p=>Math.hypot(vertex.x-p.x,vertex.y-p.y)>=1.5))
      const point=available[Math.min(available.length-1,Math.floor(random()*available.length))]
      if(!point)return robot
      position={x:point.x,y:point.y,yaw:0}
      placements.set(robot.id,position)
    }
    return {...robot,...position,hasPose:true,positionSource:'preview'}
  })
}

// For a development simulation, place the display model at its route source.
// Real telemetry always wins; this does not write a pose back to the API.
export function placeSimulatedRobotsAtRouteStart(robots,routes,data) {
  const vertices = new Map(data.vertices.map(vertex => [vertex.id,vertex]))
  return robots.map(robot => {
    if (robot.positionSource !== 'preview') return robot
    const route = routes.find(entry => entry.robotId === robot.id && entry.isSimulated)
    const first = vertices.get(route?.vertexIds?.[0])
    const second = vertices.get(route?.vertexIds?.[1])
    if (!first || !second) return robot
    return {...robot,x:first.x,y:first.y,yaw:Math.atan2(second.y-first.y,second.x-first.x)}
  })
}
