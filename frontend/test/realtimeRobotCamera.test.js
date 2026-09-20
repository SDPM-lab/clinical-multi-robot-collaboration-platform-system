import { describe, expect, it } from 'vitest'
import * as THREE from 'three'
import { getRobotCameraPose } from '@/three/navigation/realtimeRobotCamera.js'
import { RobotRouteController } from '@/three/navigation/RobotRouteController.js'

describe('realtime robot selection and camera helpers', () => {
  it('derives third-, first-person, and fixed local-follow poses from the corrected wrapper forward vector', () => {
    const position = new THREE.Vector3(2, 0, 3)
    const forward = new THREE.Vector3(1, 0, 0)
    const third = getRobotCameraPose('thirdPerson', position, forward)
    const first = getRobotCameraPose('firstPerson', position, forward)
    const local = getRobotCameraPose('localFollow', position, forward)
    expect(third.position.x).toBeLessThan(position.x)
    expect(third.target.x).toBeGreaterThan(position.x)
    expect(first.position.x).toBeGreaterThan(position.x)
    expect(first.target.x).toBeGreaterThan(first.position.x)
    expect(local.position.x).toBe(position.x)
    expect(local.position.y).toBeGreaterThan(position.y)
    expect(local.target.x).toBe(position.x)
  })

  it('stops at the destination instead of teleporting back to the route origin', () => {
    const parent = new THREE.Group()
    const controller = new RobotRouteController({
      id: 'R01', parent, points: [new THREE.Vector3(0, 0, 0), new THREE.Vector3(1, 0, 0)], color: 0xff6700,
    })
    controller.speed = 2
    controller.update(1, new THREE.PerspectiveCamera(), 1)
    expect(controller.getWorldPosition().x).toBeCloseTo(1)
    controller.update(1, new THREE.PerspectiveCamera(), 2)
    expect(controller.getWorldPosition().x).toBeCloseTo(1)
    expect(controller.getRouteState()).toMatchObject({ progress: 1, isFinalSegment: true })
    controller.dispose()
  })

  it('does not create the removed floating robot status dot', () => {
    const parent = new THREE.Group()
    const controller = new RobotRouteController({
      id: 'R03', parent, points: [new THREE.Vector3(0, 0, 0)], color: 0x00baa6,
    })
    expect(controller).not.toHaveProperty('beacon')
    expect(controller.wrapper.getObjectByName('R03 Floating Status Marker')).toBeUndefined()
    controller.dispose()
  })
})
