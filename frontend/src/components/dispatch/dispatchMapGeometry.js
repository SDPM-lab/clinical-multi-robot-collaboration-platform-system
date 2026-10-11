import { rmfToThree } from '../../config/rmfMapTransform.js'

// Compatible with HospitalMiniMap's existing SVG coordinates. All layers must
// enter through this projection; room input and robot poses are RMF metres.
export function rmfToMapPoint(point) {
  if (!Number.isFinite(point?.x) || !Number.isFinite(point?.y)) {
    throw new TypeError('Expected finite RMF x/y coordinates')
  }
  const world = rmfToThree(point)
  return { x: (world.x + 20) * 22, y: (world.z + 14) * 22 }
}

export function getMapBounds(points) {
  if (!points.length) return null
  if (points.some((point) => !Number.isFinite(point?.x) || !Number.isFinite(point?.y))) {
    throw new TypeError('Expected finite map coordinates')
  }
  const xs = points.map(({ x }) => x), ys = points.map(({ y }) => y)
  return { minX: Math.min(...xs), minY: Math.min(...ys), maxX: Math.max(...xs), maxY: Math.max(...ys) }
}

// Returns a transform into SVG viewport units, not CSS client pixels. Callers
// convert pointer positions with svg.getScreenCTM().inverse() before panning.
export function fitMapToViewport(bounds, viewport, insets = {}, padding = 24) {
  if (!bounds) return null
  const { width, height } = viewport
  const { left = 0, right = 0, top = 0, bottom = 0 } = insets
  const values = [width, height, left, right, top, bottom, padding, ...Object.values(bounds)]
  if (values.some((value) => !Number.isFinite(value)) || [left, right, top, bottom, padding].some((value) => value < 0)) {
    throw new RangeError('Invalid viewport, bounds or insets')
  }
  const availableWidth = width - left - right - padding * 2
  const availableHeight = height - top - bottom - padding * 2
  if (availableWidth <= 0 || availableHeight <= 0) return null
  if (bounds.maxX < bounds.minX || bounds.maxY < bounds.minY) throw new RangeError('Inverted bounds')
  const scale = Math.min(availableWidth / Math.max(bounds.maxX - bounds.minX, 1), availableHeight / Math.max(bounds.maxY - bounds.minY, 1))
  return {
    scale,
    x: left + padding + availableWidth / 2 - (bounds.minX + bounds.maxX) / 2 * scale,
    y: top + padding + availableHeight / 2 - (bounds.minY + bounds.maxY) / 2 * scale,
  }
}

// A room never creates a navigation destination. Only existing, explicitly
// mapped and currently dispatchable graph waypoints may be returned.
export function getRoomSelectableWaypoints(room, graph, allowedWaypointNames) {
  if (!room?.renderable || room.isDemo || room.verificationStatus !== 'source-geometry-verified') return []
  const allowed = new Set(allowedWaypointNames)
  const mapped = new Set(room.waypointNames)
  return (graph?.namedWaypoints || []).filter((point) => point.level === room.level && mapped.has(point.name) && allowed.has(point.name))
}
