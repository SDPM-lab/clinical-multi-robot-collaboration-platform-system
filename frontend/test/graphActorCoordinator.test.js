import { beforeEach, describe, expect, it } from 'vitest'
import navigation from '../public/generated/rmf-navigation-graph-1.json'
import { graphActorConfig } from '@/config/graphActorConfig.js'
import {
  buildGraphActorPlan,
  buildGraphTopology,
  GraphActorCoordinator,
  seededRandom,
} from '@/three/actors/GraphActorCoordinator.js'
import * as THREE from 'three'
import { graphActorRuntimeStore } from '@/stores/graphActorRuntimeStore.js'

describe('Graph 1 actor coordination', () => {
  beforeEach(() => graphActorRuntimeStore.clear())

  it('uses the complete exported Graph 1 without a hand-authored patrol zone', () => {
    expect(graphActorConfig.graphUrl).toMatch(/^\/generated\/rmf-navigation-graph-1\.json\?v=[a-f0-9]+$/)
    expect(graphActorConfig).not.toHaveProperty('walkingPath')
    expect(graphActorConfig).not.toHaveProperty('boundsExpansion')
    const topology = buildGraphTopology(navigation)
    expect(topology.vertices.size).toBe(navigation.vertices.length)
    expect(topology.components.map((component) => component.length)).toEqual([3, 2, 2, 2, 2, 2, 2])
    expect(topology.componentDetails.map((component) => component.laneCount)).toEqual([4, 2, 2, 2, 2, 2, 2])
  })

  it('places five actors in the five spatially best-separated high-lane components', () => {
    const { topology, definitions } = buildGraphActorPlan(navigation)
    expect(definitions).toHaveLength(5)
    expect(definitions.map((actor) => actor.startVertexId)).toEqual(['v13', 'v0', 'v10', 'v2', 'v6'])
    expect(new Set(definitions.map((actor) => actor.startVertexId)).size).toBe(5)
    expect(new Set(definitions.map((actor) => actor.componentIndex)).size).toBe(5)
    definitions.forEach((actor, index) => {
      definitions.slice(index + 1).forEach((other) => {
        expect(topology.undirected.get(actor.startVertexId).has(other.startVertexId)).toBe(false)
      })
    })
  })

  it('uses reproducible random sequences for debugging', () => {
    const first = seededRandom(101)
    const second = seededRandom(101)
    expect([first(), first(), first()]).toEqual([second(), second(), second()])
  })

  it('moves every actor along its assigned real lane after the staggered start', () => {
    const { topology, definitions } = buildGraphActorPlan(navigation)
    const controllers = definitions.map(() => ({
      actorGroup: new THREE.Group(),
      setPosition(point) { this.actorGroup.position.copy(point) },
      updateGraphMotion(delta, target, speed) {
        if (!target) return false
        const direction = target.clone().sub(this.actorGroup.position)
        const distance = direction.length()
        const step = Math.min(distance, speed * delta)
        if (distance > 0) this.actorGroup.position.addScaledVector(direction.normalize(), step)
        return distance - step <= 0.025
      },
    }))
    const starts = definitions.map((definition) => definition.point.clone())
    const coordinator = new GraphActorCoordinator({ topology, definitions, controllers })
    for (let index = 0; index < 120; index += 1) coordinator.update(0.1)
    controllers.forEach((controller, index) => {
      expect(controller.actorGroup.position.distanceTo(starts[index])).toBeGreaterThan(0.1)
      const component = new Set(topology.components[definitions[index].componentIndex])
      const laneDistances = navigation.lanes
        .filter((lane) => component.has(lane.from) && component.has(lane.to))
        .map((lane) => new THREE.Line3(
          topology.vertices.get(lane.from).point,
          topology.vertices.get(lane.to).point,
        ).closestPointToPoint(controller.actorGroup.position, true, new THREE.Vector3()).distanceTo(controller.actorGroup.position))
      expect(Math.min(...laneDistances)).toBeLessThan(1e-6)
    })
  })

  it('restores actor position and heading when switching between Overview and realtime map scenes', () => {
    const { topology, definitions } = buildGraphActorPlan(navigation)
    const makeControllers = () => definitions.map(() => ({
      actorGroup: new THREE.Group(),
      setPosition(point) { this.actorGroup.position.copy(point) },
      updateGraphMotion() { return false },
    }))
    const firstControllers = makeControllers()
    const first = new GraphActorCoordinator({ topology, definitions, controllers: firstControllers })
    firstControllers[0].actorGroup.position.add(new THREE.Vector3(0.3, 0, 0.15))
    firstControllers[0].actorGroup.rotation.y = 0.8
    const expectedPosition = firstControllers[0].actorGroup.position.clone()
    const expectedQuaternion = firstControllers[0].actorGroup.quaternion.clone()
    first.dispose()

    const secondControllers = makeControllers()
    const second = new GraphActorCoordinator({ topology, definitions, controllers: secondControllers })
    expect(secondControllers[0].actorGroup.position.distanceTo(expectedPosition)).toBeLessThan(1e-9)
    expect(secondControllers[0].actorGroup.quaternion.angleTo(expectedQuaternion)).toBeLessThan(1e-9)
    second.dispose()
  })
})
