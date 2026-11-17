import { describe, expect, it } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'
import { laneDisplayPoints, routeDisplayPoints, shortestLanePath, validateDispatchMapping, waypointDisplayPoint } from '../src/components/dispatch/dispatchRouteMapping.js'
import { dispatchTaskLocations, dispatchWaypointLabels, PPO_TASK_WAYPOINT_IDS } from '../src/config/dispatchDestinations.js'
import { dispatchLocations } from '../src/config/dispatchMap.js'
import { TASK_LOCATION_IDS } from '../src/config/taskTypes.js'

const root = path.resolve(import.meta.dirname, '..')
const graph = JSON.parse(fs.readFileSync(path.join(root, 'public/generated/rmf-navigation.json'), 'utf8'))
const mapping = JSON.parse(fs.readFileSync(path.join(root, 'public/generated/dispatch-route-mapping.json'), 'utf8'))
const byName = new Map(graph.namedWaypoints.map((vertex) => [vertex.name, vertex.id]))

describe('L1 Traffic Editor to GLB display mapping', () => {
  it('maps every directed lane to connected GLB display segments', () => {
    expect(validateDispatchMapping(mapping, graph)).toBe(true)
    expect(Object.keys(mapping.lanes)).toHaveLength(graph.lanes.length)
    expect(mapping.unmappedLanes).toEqual([])
    expect(mapping.audit.glbRouteMeshesVerified).toBe(103)
    expect(mapping.audit.unmappedVertexIds).toEqual([])
    expect(mapping.audit.duplicateVertexAnchors).toEqual({})
    expect(mapping.audit.sharedDisplaySegments).toEqual([])
    for (const lane of graph.lanes) {
      const points = laneDisplayPoints(mapping, lane.id)
      expect(points.length).toBeGreaterThanOrEqual(2)
      expect(points[0]).toEqual(waypointDisplayPoint(mapping, lane.from))
      expect(points.at(-1)).toEqual(waypointDisplayPoint(mapping, lane.to))
    }
  })

  it.each([
    ['consult_2_1', 'nurse_station'],
    ['reception_back', 'charging_station_1'],
    ['reception_back', 'pharmacy'],
  ])('renders the reachable route %s to %s through shared display positions', (from, to) => {
    const laneIds = shortestLanePath(graph, byName.get(from), byName.get(to), mapping)
    expect(laneIds.length).toBeGreaterThan(0)
    const points = routeDisplayPoints(mapping, laneIds)
    expect(points[0]).toEqual(waypointDisplayPoint(mapping, byName.get(from)))
    expect(points.at(-1)).toEqual(waypointDisplayPoint(mapping, byName.get(to)))
    for (const laneId of laneIds) {
      for (const point of laneDisplayPoints(mapping, laneId)) expect(points).toContainEqual(point)
    }
  })

  it('keeps routes to Ward B and the corrected right corridor reachable', () => {
    for (const [from, to] of [['consult_2_1', 'ward_b_1'], ['reception_back', 'waste_return_1'], ['waste_return_1', 'therapy_room']]) {
      expect(shortestLanePath(graph, byName.get(from), byName.get(to), mapping).length).toBeGreaterThan(0)
    }
  })

  it('offers every dispatch destination at a mapped and reachable TE waypoint', () => {
    expect(new Set(dispatchTaskLocations).size).toBe(dispatchTaskLocations.length)
    expect(dispatchTaskLocations).toHaveLength(16)
    expect(PPO_TASK_WAYPOINT_IDS).toHaveLength(16)
    expect(PPO_TASK_WAYPOINT_IDS[0]).toBe('charging_station_2')
    expect(PPO_TASK_WAYPOINT_IDS.every(waypoint => dispatchWaypointLabels[waypoint])).toBe(true)
    expect(PPO_TASK_WAYPOINT_IDS.every(waypoint => dispatchLocations[waypoint])).toBe(true)
    for (const profile of Object.values(TASK_LOCATION_IDS)) {
      expect(profile.sources).not.toContain('charging_station_2')
      expect(profile.destinations).not.toContain('charging_station_2')
    }
    for (const waypoint of Object.keys(dispatchWaypointLabels)) {
      const id = byName.get(waypoint)
      expect(id, waypoint).toBeDefined()
      expect(waypointDisplayPoint(mapping, id), waypoint).not.toBeNull()
      if (waypoint !== 'reception_back') {
        expect(shortestLanePath(graph, byName.get('reception_back'), id, mapping).length, waypoint).toBeGreaterThan(0)
        expect(shortestLanePath(graph, id, byName.get('reception_back'), mapping).length, waypoint).toBeGreaterThan(0)
      }
    }
  })
})
