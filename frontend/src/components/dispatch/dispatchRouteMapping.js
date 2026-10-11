// GLB coordinates are presentation coordinates. Only Graph 0 lanes determine
// connectivity and direction; unused GLB branches are never navigable.
export function validateDispatchMapping(mapping, graph) {
  if (mapping?.schemaVersion !== 1 || mapping.level !== 'L1' || mapping.graphIndex !== graph?.graphIndex) return false
  if (!mapping.displayNodes || !mapping.displayEdges || !mapping.vertices || !mapping.lanes) return false
  for (const vertex of graph.vertices || []) {
    const mapped = mapping.vertices[vertex.id]
    if (!mapped || mapped.name !== vertex.name || mapped.sourceVertexIndex !== vertex.sourceVertexIndex
      || mapped.sourcePosition?.[0] !== vertex.x || mapped.sourcePosition?.[1] !== vertex.y) return false
    if (mapped.displayNode && !mapping.displayNodes[mapped.displayNode]) return false
  }
  for (const lane of graph.lanes || []) {
    const mapped = mapping.lanes[lane.id]
    if (!mapped) {
      if (!mapping.unmappedLanes?.some((entry) => entry.laneId === lane.id)) return false
      continue
    }
    if (mapped.from !== lane.from || mapped.to !== lane.to || mapped.displayNodes?.length < 2) return false
    if (mapped.displayNodes[0] !== mapping.vertices[lane.from]?.displayNode
      || mapped.displayNodes.at(-1) !== mapping.vertices[lane.to]?.displayNode) return false
    for (let index = 1; index < mapped.displayNodes.length; index++) {
      const a = mapped.displayNodes[index - 1], b = mapped.displayNodes[index]
      if (!Object.values(mapping.displayEdges).some((edge) => edge.nodes.includes(a) && edge.nodes.includes(b))) return false
    }
  }
  return true
}

export function shortestLanePath(graph, from, to, mapping) {
  if (!graph?.vertices?.some((vertex) => vertex.id === from) || !graph.vertices.some((vertex) => vertex.id === to)) return []
  const queue = [{ vertex: from, lanes: [] }], visited = new Set([from])
  for (let index = 0; index < queue.length; index++) {
    const current = queue[index]
    if (current.vertex === to) return current.lanes
    for (const neighbor of graph.adjacency[current.vertex] || []) {
      if (!mapping.lanes[neighbor.laneId] || visited.has(neighbor.neighborVertexId)) continue
      visited.add(neighbor.neighborVertexId)
      queue.push({ vertex: neighbor.neighborVertexId, lanes: [...current.lanes, neighbor.laneId] })
    }
  }
  return []
}

export function laneDisplayPoints(mapping, laneId) {
  return (mapping.lanes[laneId]?.displayNodes || []).map((name) => mapping.displayNodes[name]?.position).filter(Boolean)
}

export function routeDisplayPoints(mapping, laneIds) {
  const result = []
  for (const laneId of laneIds) {
    const points = laneDisplayPoints(mapping, laneId)
    if (result.length && points.length && result.at(-1).some((value, index) => Math.abs(value - points[0][index]) > 1e-5)) return []
    result.push(...(result.length ? points.slice(1) : points))
  }
  return result
}

export function waypointDisplayPoint(mapping, vertexId) {
  const key = mapping.vertices[vertexId]?.displayNode
  return key ? mapping.displayNodes[key]?.position || null : null
}
