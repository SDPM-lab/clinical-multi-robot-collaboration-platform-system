import * as THREE from 'three'
import { rmfToThree } from '@/config/rmfMapTransform.js'
import { graphActorConfig } from '@/config/graphActorConfig.js'
import { graphActorRuntimeStore } from '@/stores/graphActorRuntimeStore.js'

const laneKey = (from, to) => [from, to].sort().join(':')
const randomBetween = (random, [minimum, maximum]) => minimum + random() * (maximum - minimum)

export const seededRandom = (seed) => {
  let state = seed >>> 0
  return () => {
    state = (Math.imul(state, 1664525) + 1013904223) >>> 0
    return state / 4294967296
  }
}

export const buildGraphTopology = (navigation) => {
  if (navigation.graphIndex !== graphActorConfig.graphIndex) {
    throw new Error(`人物只允許使用 Traffic Editor Graph ${graphActorConfig.graphIndex}。`)
  }

  const vertices = new Map(navigation.vertices.map((vertex) => {
    const world = rmfToThree(vertex)
    return [vertex.id, {
      ...vertex,
      point: new THREE.Vector3(world.x, graphActorConfig.floorY || 0, world.z),
    }]
  }))
  const adjacency = new Map([...vertices.keys()].map((id) => [id, []]))
  const undirected = new Map([...vertices.keys()].map((id) => [id, new Set()]))

  navigation.lanes.forEach((lane) => {
    if (!vertices.has(lane.from) || !vertices.has(lane.to)) return
    if (!adjacency.get(lane.from).some((entry) => entry.to === lane.to)) {
      adjacency.get(lane.from).push({ id: lane.id, from: lane.from, to: lane.to })
    }
    undirected.get(lane.from).add(lane.to)
    undirected.get(lane.to).add(lane.from)
  })

  const components = []
  const visited = new Set()
  for (const start of vertices.keys()) {
    if (visited.has(start)) continue
    const queue = [start]
    const ids = []
    visited.add(start)
    while (queue.length) {
      const current = queue.shift()
      ids.push(current)
      undirected.get(current).forEach((neighbor) => {
        if (visited.has(neighbor)) return
        visited.add(neighbor)
        queue.push(neighbor)
      })
    }
    if (ids.some((id) => adjacency.get(id).length > 0)) components.push(ids)
  }
  const componentDetails = components.map((ids) => ({
    ids,
    laneCount: navigation.lanes.filter((lane) => ids.includes(lane.from) && ids.includes(lane.to)).length,
  })).sort((a, b) => b.laneCount - a.laneCount || b.ids.length - a.ids.length || a.ids[0].localeCompare(b.ids[0]))
  return {
    vertices,
    adjacency,
    undirected,
    components: componentDetails.map((component) => component.ids),
    componentDetails,
    signature: [
      navigation.graphIndex,
      ...navigation.vertices.map((vertex) => `${vertex.id}:${vertex.x}:${vertex.y}`),
      ...navigation.lanes.map((lane) => `${lane.from}>${lane.to}`),
    ].join('|'),
  }
}

const minimumPairDistance = (ids, vertices) => {
  let minimum = Infinity
  for (let first = 0; first < ids.length; first += 1) {
    for (let second = first + 1; second < ids.length; second += 1) {
      minimum = Math.min(minimum, vertices.get(ids[first]).point.distanceTo(vertices.get(ids[second]).point))
    }
  }
  return minimum
}

const nonAdjacent = (ids, undirected) => ids.every((id, index) => (
  ids.slice(index + 1).every((other) => !undirected.get(id).has(other))
))

const combinations = (values, count, start = 0, prefix = [], output = []) => {
  if (prefix.length === count) {
    output.push([...prefix])
    return output
  }
  for (let index = start; index <= values.length - (count - prefix.length); index += 1) {
    prefix.push(values[index])
    combinations(values, count, index + 1, prefix, output)
    prefix.pop()
  }
  return output
}

const cartesianSelections = (groups, index = 0, prefix = [], output = []) => {
  if (index === groups.length) {
    output.push([...prefix])
    return output
  }
  groups[index].forEach((value) => {
    prefix.push(value)
    cartesianSelections(groups, index + 1, prefix, output)
    prefix.pop()
  })
  return output
}

export const selectActorStarts = (topology, actorCount = 3) => {
  const { components, componentDetails, vertices, undirected } = topology
  if (components.length === 0) throw new Error('Graph 1 沒有可供人物行走的 Lane。')
  if (vertices.size < actorCount) throw new Error(`Graph 1 只有 ${vertices.size} 個 Vertex，無法放置 ${actorCount} 位人物。`)

  let candidates
  if (components.length >= actorCount) {
    const ranked = componentDetails || components.map((ids) => ({ ids, laneCount: ids.length }))
    const cutoffLaneCount = ranked[actorCount - 1].laneCount
    const mandatory = ranked.filter((component) => component.laneCount > cutoffLaneCount)
    const tied = ranked.filter((component) => component.laneCount === cutoffLaneCount)
    const optionalCount = actorCount - mandatory.length
    candidates = combinations(tied, optionalCount)
      .map((selection) => [...mandatory, ...selection].map((component) => component.ids))
      .flatMap((componentSet) => cartesianSelections(componentSet))
  } else {
    candidates = combinations([...new Set(components.flat())], actorCount)
  }
  const preferred = candidates.filter((ids) => nonAdjacent(ids, undirected))
  const pool = preferred.length ? preferred : candidates
  pool.sort((a, b) => (
    minimumPairDistance(b, vertices) - minimumPairDistance(a, vertices)
    || a.join(':').localeCompare(b.join(':'))
  ))
  return pool[0]
}

export const buildGraphActorPlan = (navigation, config = graphActorConfig) => {
  const topology = buildGraphTopology(navigation)
  const starts = selectActorStarts(topology, config.actorCount)
  const definitions = starts.map((startVertexId, index) => ({
    id: `N${index + 1}`,
    name: `Nurse ${String(index + 1).padStart(2, '0')}`,
    seed: config.seeds[index],
    animationOffset: config.animationOffsets[index],
    startVertexId,
    componentIndex: topology.components.findIndex((component) => component.includes(startVertexId)),
    point: topology.vertices.get(startVertexId).point.clone(),
  }))
  return { topology, definitions }
}

export class GraphActorCoordinator {
  constructor({ topology, definitions, controllers, config = graphActorConfig, runtimeStore = graphActorRuntimeStore }) {
    this.topology = topology
    this.config = config
    this.runtimeStore = runtimeStore
    this.runtimeStore.prepare(topology.signature)
    this.vertexReservations = new Map()
    this.laneReservations = new Map()
    this.states = definitions.map((definition, index) => {
      const snapshot = this.runtimeStore.get(definition.id)
      const component = topology.components[definition.componentIndex]
      const snapshotIsValid = Boolean(
        snapshot
        && component.includes(snapshot.currentVertexId)
        && (!snapshot.targetVertexId || component.includes(snapshot.targetVertexId)),
      )
      const state = {
        ...definition,
        controller: controllers[index],
        random: seededRandom(definition.seed),
        currentVertexId: snapshotIsValid ? snapshot.currentVertexId : definition.startVertexId,
        previousVertexId: snapshotIsValid ? snapshot.previousVertexId : null,
        targetVertexId: snapshotIsValid ? snapshot.targetVertexId : null,
        activeLaneKey: snapshotIsValid ? snapshot.activeLaneKey : null,
        speed: snapshotIsValid ? snapshot.speed : randomBetween(seededRandom(definition.seed + 11), config.walkSpeed),
        waitRemaining: snapshotIsValid ? snapshot.waitRemaining : definition.animationOffset,
      }
      this.vertexReservations.set(state.currentVertexId, state.id)
      if (state.targetVertexId) {
        this.vertexReservations.set(state.targetVertexId, state.id)
        this.laneReservations.set(state.activeLaneKey || laneKey(state.currentVertexId, state.targetVertexId), state.id)
      }
      state.controller.setPosition(
        snapshotIsValid ? new THREE.Vector3().fromArray(snapshot.position) : definition.point,
      )
      if (snapshotIsValid && snapshot.quaternion) state.controller.actorGroup.quaternion.fromArray(snapshot.quaternion)
      return state
    })
  }

  isSafeTarget(state, lane) {
    const vertexOwner = this.vertexReservations.get(lane.to)
    if (vertexOwner && vertexOwner !== state.id) return false
    const occupiedLane = this.laneReservations.get(laneKey(lane.from, lane.to))
    if (occupiedLane && occupiedLane !== state.id) return false
    const target = this.topology.vertices.get(lane.to).point
    return this.states.every((other) => (
      other === state
      || target.distanceTo(other.controller.actorGroup.position) >= this.config.minActorDistance
    ))
  }

  chooseNextLane(state) {
    const outgoing = this.topology.adjacency.get(state.currentVertexId) || []
    const forward = outgoing.filter((lane) => lane.to !== state.previousVertexId)
    const availableForward = forward.filter((lane) => this.isSafeTarget(state, lane))
    const atEndpoint = forward.length === 0
    const availableReverse = atEndpoint ? outgoing.filter((lane) => this.isSafeTarget(state, lane)) : []
    const candidates = availableForward.length ? availableForward : availableReverse
    if (!candidates.length) return false

    const lane = candidates[Math.floor(state.random() * candidates.length)]
    state.targetVertexId = lane.to
    state.activeLaneKey = laneKey(lane.from, lane.to)
    state.speed = randomBetween(state.random, this.config.walkSpeed)
    this.vertexReservations.set(lane.to, state.id)
    this.laneReservations.set(state.activeLaneKey, state.id)
    return true
  }

  wouldBreachSpacing(state, target, delta) {
    const current = state.controller.actorGroup.position
    const direction = target.clone().sub(current).setY(0)
    const length = direction.length()
    if (length <= 0) return false
    const next = current.clone().addScaledVector(direction.normalize(), Math.min(length, state.speed * delta))
    return this.states.some((other) => (
      other !== state
      && next.distanceTo(other.controller.actorGroup.position) < this.config.minActorDistance
    ))
  }

  update(delta) {
    const safeDelta = Math.max(0, Number(delta) || 0)
    this.states.forEach((state) => {
      if (state.waitRemaining > 0) {
        state.waitRemaining = Math.max(0, state.waitRemaining - safeDelta)
        state.controller.updateGraphMotion(safeDelta)
        return
      }
      if (!state.targetVertexId && !this.chooseNextLane(state)) {
        state.waitRemaining = 0.35
        state.controller.updateGraphMotion(safeDelta)
        return
      }

      const target = this.topology.vertices.get(state.targetVertexId).point
      if (this.wouldBreachSpacing(state, target, safeDelta)) {
        state.controller.updateGraphMotion(safeDelta)
        return
      }
      const reached = state.controller.updateGraphMotion(safeDelta, target, state.speed)
      if (!reached) return

      const departed = state.currentVertexId
      this.vertexReservations.delete(departed)
      this.laneReservations.delete(state.activeLaneKey)
      state.previousVertexId = departed
      state.currentVertexId = state.targetVertexId
      state.targetVertexId = null
      state.activeLaneKey = null
      state.waitRemaining = randomBetween(state.random, this.config.idleDuration)
    })
  }

  dispose() {
    this.states.forEach((state) => this.runtimeStore.save(state.id, {
      currentVertexId: state.currentVertexId,
      previousVertexId: state.previousVertexId,
      targetVertexId: state.targetVertexId,
      activeLaneKey: state.activeLaneKey,
      speed: state.speed,
      waitRemaining: state.waitRemaining,
      position: state.controller.actorGroup.position.toArray(),
      quaternion: state.controller.actorGroup.quaternion.toArray(),
    }))
    this.vertexReservations.clear()
    this.laneReservations.clear()
    this.states = []
  }
}
