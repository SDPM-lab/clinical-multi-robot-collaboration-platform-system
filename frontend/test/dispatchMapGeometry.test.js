// @vitest-environment node
import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { hospitalRoomLayout } from '../src/data/hospitalRoomLayout.js'
import { fitMapToViewport, getMapBounds, getRoomSelectableWaypoints, rmfToMapPoint } from '../src/components/dispatch/dispatchMapGeometry.js'

const root = new URL('../../', import.meta.url)
const floorplan = JSON.parse(readFileSync(new URL('frontend/public/generated/hospital-floorplan.json', root), 'utf8'))
const graph = JSON.parse(readFileSync(new URL('frontend/public/generated/rmf-navigation.json', root), 'utf8'))
const roomById = (id) => floorplan.rooms.find((room) => room.id === id)

describe('source-derived dispatch floorplan', () => {
  it('is reproducibly tied to the current building, graph and room configuration', () => {
    for (const [path, hash] of Object.entries(floorplan.sourceHashes)) {
      expect(createHash('sha256').update(readFileSync(new URL(path, root))).digest('hex'), path).toBe(hash)
    }
    expect(floorplan.coordinateFrame).toBe('rmf')
    expect(floorplan.units).toBe('metres')
    expect(floorplan.validation.matchedWaypoints).toBe(graph.namedWaypoints.length)
    expect(floorplan.validation.maxWaypointErrorMeters).toBeLessThan(1e-6)
    // The 10 m image measurement is 360.283 pixels, not occupancy-map resolution.
    expect(floorplan.transform.imageScale).toBeCloseTo(10 / 360.283, 12)
    expect(floorplan.transform.imageScale).not.toBe(0.02775)
  })

  it('keeps incomplete boundaries out of renderable geometry', () => {
    expect(floorplan.rooms.filter((room) => room.renderable)).toHaveLength(14)
    for (const id of ['blood-draw', 'nurse-station', 'reception', 'pharmacy']) {
      expect(roomById(id).renderable).toBe(false)
      expect(roomById(id).polygon).toEqual([])
      expect(roomById(id).issues.length).toBeGreaterThan(0)
    }
    expect(roomById('blood-draw').candidatePolygon).toHaveLength(4)
    expect(roomById('pharmacy').candidatePolygon).toEqual([])
  })

  it('uses the revised navigation names without reverting to image labels', () => {
    expect(new Set(floorplan.rooms.map(({ id }) => id)).size).toBe(floorplan.rooms.length)
    for (const room of floorplan.rooms) {
      const source = hospitalRoomLayout.rooms.find(({ id }) => id === room.id)
      expect(room.boundaryVertexIndices).toEqual(source.boundaryVertexIndices)
      expect(room.waypointNames).toEqual(source.waypointNames)
      expect(room.isDemo).toBe(false)
      if (room.renderable) {
        expect(room.verificationStatus).toBe('source-geometry-verified')
        expect(room.issues).toEqual([])
        expect(room.boundaryEvidence.every((edge) => edge.maxDistanceToSourceMeters <= 0.12)).toBe(true)
      }
    }
    expect(roomById('consultation-3').label).toBe('診間 3')
    expect(roomById('consultation-2').label).toBe('診間 2')
    expect(roomById('pantry').label).toBe('茶水間')
    expect(roomById('clothes-return').label).toBe('衣物回收區')
    expect(roomById('x-ray').nameAuthority).toBe('current-navigation-and-frontend-names')
    expect(floorplan).not.toHaveProperty('referenceImage')
    expect(floorplan.rooms.every((room) => !('semanticsStatus' in room))).toBe(true)
  })

  it('returns only explicitly mapped, permitted, same-floor graph waypoints', () => {
    const charging = roomById('charging')
    const selected = getRoomSelectableWaypoints(charging, graph, ['charging_station_1'])
    expect(selected.map(({ name }) => name)).toEqual(['charging_station_1'])
    expect(selected[0]).toBe(graph.namedWaypoints.find(({ name }) => name === 'charging_station_1'))
    expect(getRoomSelectableWaypoints(charging, graph, ['pharmacy'])).toEqual([])
    expect(getRoomSelectableWaypoints({ ...charging, level: 'L2' }, graph, ['charging_station_1'])).toEqual([])
    expect(getRoomSelectableWaypoints({ ...charging, isDemo: true }, graph, ['charging_station_1'])).toEqual([])
    expect(getRoomSelectableWaypoints(roomById('pharmacy'), graph, ['pharmacy'])).toEqual([])
  })
})

describe('shared projection and unobscured camera fitting', () => {
  it('retains the existing SVG coordinate convention for all RMF data', () => {
    expect(rmfToMapPoint({ x: 19.860754013061523, y: -13.426342964172363 })).toEqual({ x: 440, y: 308 })
    const first = rmfToMapPoint({ x: 10, y: -10 })
    const second = rmfToMapPoint({ x: 11, y: -11 })
    expect(second.x - first.x).toBeCloseTo(22)
    expect(second.y - first.y).toBeCloseTo(22)
    expect(() => rmfToMapPoint({ x: NaN, y: 0 })).toThrow()
  })

  it.each([
    [{ width: 1440, height: 838 }, { left: 400, bottom: 48 }],
    [{ width: 1024, height: 706 }, { left: 360, bottom: 240 }],
    [{ width: 390, height: 420 }, {}],
  ])('fits the full floor and every waypoint clear of overlays in %j', (viewport, insets) => {
    const points = [...floorplan.footprint, ...graph.vertices, ...floorplan.rooms.flatMap(({ polygon }) => polygon)].map(rmfToMapPoint)
    const original = JSON.stringify(points)
    const camera = fitMapToViewport(getMapBounds(points), viewport, insets)
    for (const point of points) {
      const x = camera.x + point.x * camera.scale, y = camera.y + point.y * camera.scale
      expect(x).toBeGreaterThanOrEqual((insets.left || 0) + 24 - 1e-8)
      expect(x).toBeLessThanOrEqual(viewport.width - (insets.right || 0) - 24 + 1e-8)
      expect(y).toBeGreaterThanOrEqual((insets.top || 0) + 24 - 1e-8)
      expect(y).toBeLessThanOrEqual(viewport.height - (insets.bottom || 0) - 24 + 1e-8)
    }
    expect(JSON.stringify(points)).toBe(original)
  })

  it('handles an unmeasured/hidden viewport without invalid transforms', () => {
    expect(getMapBounds([])).toBeNull()
    expect(fitMapToViewport(null, { width: 100, height: 100 })).toBeNull()
    const bounds = getMapBounds([{ x: 10, y: 20 }])
    expect(fitMapToViewport(bounds, { width: 0, height: 0 })).toBeNull()
    expect(fitMapToViewport(bounds, { width: 300, height: 200 }, { left: 360 })).toBeNull()
    expect(Number.isFinite(fitMapToViewport(bounds, { width: 300, height: 200 }).scale)).toBe(true)
    expect(() => fitMapToViewport(bounds, { width: NaN, height: 200 })).toThrow()
  })
})
