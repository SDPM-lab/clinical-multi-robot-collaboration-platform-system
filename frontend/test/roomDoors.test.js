import { describe, expect, it } from 'vitest'
import * as THREE from 'three'
import navigation from '../public/generated/rmf-navigation.json'
import { buildRoomLabels, RoomLabelLayer } from '@/three/navigation/RoomLabelLayer.js'
import { RobotRouteController } from '@/three/navigation/RobotRouteController.js'
import { RmfDoorController } from '@/three/navigation/RmfDoorController.js'

it('builds one label per mapped room and includes rooms known only by their doors', () => {
  const labels = buildRoomLabels(navigation)
  const names = labels.map((entry) => entry.label)
  expect(new Set(names).size).toBe(names.length)
  expect(names).toContain('Ward A')
  expect(names).toContain('Pantry')
  expect(names.filter((name) => name.includes('Restroom'))).toEqual(["Men's Restroom", "Women's Restroom"])
  expect(names).toContain('Consultation Room 3')
  expect(names).toContain('Waste Return')
  expect(names).not.toContain('Ward C')
  expect(labels.find((entry) => entry.label === 'Ward A').x).toBeCloseTo((6.511714402289311 + 6.467082821004599) / 2)
})

describe('door approach animation', () => {
  it('opens the moving leaf before crossing and leaves the frame in place', () => {
    const root = new THREE.Group()
    const joint = new THREE.Group(); joint.name = 'ward_a_door__right_joint'; joint.position.set(2, 0, 3)
    const frame = new THREE.Group(); frame.name = 'ward_a_door_frame'; frame.position.x = .5
    const leaf = new THREE.Group(); leaf.name = 'ward_a_door__right__proxy'; leaf.position.x = -.5
    joint.add(frame, leaf); root.add(joint)
    const frameBefore = frame.getWorldPosition(new THREE.Vector3())
    const controller = new RmfDoorController({ model: root, doorNames: ['ward_a_door'] })
    expect(frame.parent).toBe(root)
    controller.update(1, [new THREE.Vector3(2, 0, 3)])
    expect(joint.rotation.y).toBeGreaterThan(0)
    expect(frame.getWorldPosition(new THREE.Vector3()).distanceTo(frameBefore)).toBeLessThan(1e-8)
    const openAngle = joint.rotation.y
    controller.update(1, [new THREE.Vector3(20, 0, 20)])
    expect(joint.rotation.y).toBeLessThan(openAngle)
    controller.dispose()
    expect(joint.rotation.y).toBe(0)
  })
})

it('holds robot progress until the door is open, then resumes', () => {
  const model = new THREE.Group()
  const joint = new THREE.Group()
  joint.name = 'test__right_joint'
  model.add(joint)
  const doors = new RmfDoorController({ model, doorNames: ['test'] })
  const robot = new RobotRouteController({ id: 'R01', parent: new THREE.Group(), points: [new THREE.Vector3(-2, 0, 0), new THREE.Vector3(2, 0, 0)], color: 0xffffff })
  robot.update(10, null, 0, doors)
  expect(robot.waitingForDoor).toBe(true)
  expect(robot.getWorldPosition().x).toBeLessThanOrEqual(-1.15)
  const stopped = robot.distance
  robot.update(.1, null, 0, doors)
  expect(robot.distance).toBe(stopped)
  for (let i = 0; i < 10; i++) doors.update(.1, [robot.getWorldPosition()])
  robot.update(1, null, 0, doors)
  expect(robot.waitingForDoor).toBe(false)
  expect(robot.distance).toBeGreaterThan(stopped)
  robot.dispose()
  doors.dispose()
})


it('anchors restroom labels to their entrance doors on the same corridor', () => {
  const labels = buildRoomLabels(navigation)
  const men = labels.find((entry) => entry.id === 'restroom_men')
  const women = labels.find((entry) => entry.id === 'restroom_women')
  expect(men.x).toBeCloseTo(23.416814)
  expect(women.x).toBeCloseTo(27.164965)
  expect(Math.abs(men.y - women.y)).toBeLessThan(.03)
})

it('keeps crowded room labels within one row of their door instead of cascading down the map', () => {
  const container = document.createElement('div')
  const camera = new THREE.PerspectiveCamera(50, 1, .1, 100)
  camera.position.z = 10
  camera.updateMatrixWorld()
  const canvas = { getBoundingClientRect: () => ({ width: 800, height: 800 }) }
  const layer = new RoomLabelLayer({ data: navigation, container, camera, canvas })
  for (const entry of layer.entries) {
    entry.point.set(0, 0, 0)
    Object.defineProperty(entry.root, 'offsetWidth', { value: 150 })
    Object.defineProperty(entry.root, 'offsetHeight', { value: 36 })
  }
  layer.update()
  for (const entry of layer.entries) {
    const y = Number(entry.root.style.transform.match(/translate3d\([^,]+, ([^p]+)px/)[1])
    expect(Math.abs(y - 400)).toBeLessThanOrEqual(42)
  }
  layer.dispose()
})
