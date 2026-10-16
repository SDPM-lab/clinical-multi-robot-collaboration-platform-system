import { describe, expect, it, vi } from 'vitest'
import * as THREE from 'three'
import { getRobotCameraPose } from '@/three/navigation/realtimeRobotCamera.js'
import { RobotRouteController } from '@/three/navigation/RobotRouteController.js'
import { loadRobotAsset } from '@/three/robot/robotModelAssets.js'

vi.mock('@/three/robot/robotModelAssets.js', () => ({
  DEFAULT_ROBOT_ASSET: 'AGIBOT_A2D',
  loadRobotAsset: vi.fn(),
}))

describe('realtime robot selection and camera helpers', () => {
  it('reuses the Robot Status model for map robots and keeps shared geometry alive', async () => {
    const geometry = new THREE.BoxGeometry(1, 2, 1)
    const scene = new THREE.Group()
    scene.name = 'AGIBOT_A2D'
    scene.add(new THREE.Mesh(geometry, new THREE.MeshStandardMaterial()))
    vi.mocked(loadRobotAsset).mockResolvedValue({ scene, animations: [] })
    const parent = new THREE.Group()
    const first = new RobotRouteController({ id: 'R01', parent, color: 0xff6700 })
    const second = new RobotRouteController({ id: 'R02', parent, color: 0xff6700 })
    await Promise.all([first.load(), second.load()])
    expect(loadRobotAsset).toHaveBeenCalledWith('AGIBOT_A2D')
    expect(first.model.rotation.y).toBeCloseTo(-Math.atan2(1, 0.28))
    expect(first.model.children[0].geometry).toBe(geometry)
    expect(second.model.children[0].geometry).toBe(geometry)
    const disposeGeometry = vi.spyOn(geometry, 'dispose')
    first.dispose()
    expect(disposeGeometry).not.toHaveBeenCalled()
    expect(second.model.children[0].geometry).toBe(geometry)
    second.dispose()
    scene.children[0].material.dispose()
    geometry.dispose()
  })

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
