import { describe, expect, it } from 'vitest'
import * as THREE from 'three'
import navigation from '../public/generated/rmf-navigation-graph-1.json'
import { ACTOR_FORWARD_AXIS_OFFSET, baymaxConfig } from '@/config/baymaxNurseConfig.js'
import { rmfToThree } from '@/config/rmfMapTransform.js'
import { BaymaxNurseController } from '@/three/actors/BaymaxNurseController.js'

describe('BaymaxNurseController path movement', () => {
  it('moves by speed multiplied by delta without changing floor height', () => {
    const actorGroup = new THREE.Group()
    const controller = new BaymaxNurseController({ actorGroup })
    controller.setPath([[0, 4, 0], [2, 9, 0]])

    controller.update(1)

    expect(actorGroup.position.x).toBeCloseTo(baymaxConfig.speed)
    expect(actorGroup.position.y).toBe(baymaxConfig.floorY)
    expect(actorGroup.position.z).toBeCloseTo(0)
  })

  it('moves between two adjacent Graph 1 vertices without teleporting', () => {
    const actorGroup = new THREE.Group()
    const controller = new BaymaxNurseController({ actorGroup })
    const lane = navigation.lanes[0]
    const vertices = new Map(navigation.vertices.map((vertex) => [vertex.id, vertex]))
    const path = [vertices.get(lane.from), vertices.get(lane.to)].map((vertex) => {
      const point = rmfToThree(vertex)
      return [point.x, point.y, point.z]
    })
    controller.setPath(path)

    const before = actorGroup.position.clone()
    controller.update(0.5)

    expect(actorGroup.position.distanceTo(before)).toBeCloseTo(
      baymaxConfig.speed * 0.5,
    )
  })

  it('controls actor visibility independently', () => {
    const actorGroup = new THREE.Group()
    const controller = new BaymaxNurseController({ actorGroup })

    controller.setVisible(false)
    expect(actorGroup.visible).toBe(false)
    controller.setVisible(true)
    expect(actorGroup.visible).toBe(true)
  })

  it('separates route motion from the native +X model forward-axis correction', () => {
    const actorMotionWrapper = new THREE.Group()
    const controller = new BaymaxNurseController({ actorGroup: actorMotionWrapper })

    expect(controller.actorMotionWrapper).toBe(actorMotionWrapper)
    expect(controller.actorModelWrapper.parent).toBe(actorMotionWrapper)
    expect(controller.actorModelWrapper.rotation.y).toBeCloseTo(ACTOR_FORWARD_AXIS_OFFSET)

    controller.setPath([[0, 0, 0], [2, 0, 0]])
    controller.update(1)
    const nativeModelForward = new THREE.Vector3(1, 0, 0)
      .applyQuaternion(controller.actorModelWrapper.quaternion)
      .applyQuaternion(controller.actorMotionWrapper.quaternion)

    expect(nativeModelForward.x).toBeGreaterThan(0.99)
    expect(Math.abs(nativeModelForward.z)).toBeLessThan(0.01)
  })

  it('turns the corrected chest forward when returning and keeps that heading while idle', () => {
    const actorMotionWrapper = new THREE.Group()
    const controller = new BaymaxNurseController({ actorGroup: actorMotionWrapper })
    controller.setPath([[2, 0, 0], [0, 0, 0]])
    controller.update(1)

    const correctedForward = new THREE.Vector3(1, 0, 0)
      .applyQuaternion(controller.actorModelWrapper.quaternion)
      .applyQuaternion(controller.actorMotionWrapper.quaternion)
    expect(correctedForward.x).toBeLessThan(-0.99)

    const idleHeading = actorMotionWrapper.quaternion.clone()
    controller.updateGraphMotion(0.5)
    expect(actorMotionWrapper.quaternion.angleTo(idleHeading)).toBeCloseTo(0)
  })
})
