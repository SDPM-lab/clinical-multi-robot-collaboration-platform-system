import * as THREE from 'three'
import { rmfToThree } from '@/config/rmfMapTransform.js'

const OPEN_DISTANCE = 1.7
const OPEN_ANGLE = 1.35
const MODEL_DOOR_ALIASES = { consult_1_door: 'consult_a_door', consult_2_door: 'ward_d_door', waste_return_door: 'storage_door', clothes_return_door: 'recycling_room' }

export class RmfDoorController {
  constructor({ model, doorNames, doors = [] }) {
    model.updateMatrixWorld(true)
    this.doors = doorNames.flatMap((name) => {
      const modelName = model.getObjectByName(`${name}__right_joint`) || model.getObjectByName(`${name}__left_joint`) ? name : (MODEL_DOOR_ALIASES[name] || name)
      const joints = ['left', 'right'].map((side) => ({ side, joint: model.getObjectByName(`${modelName}__${side}_joint`) })).filter(({ joint }) => joint)
      if (!joints.length) return []
      // The exported room-door frame is parented to the moving joint. Keep the frame fixed.
      for (const { joint } of joints) {
        for (const child of [...joint.children]) {
          if (/_frame$/i.test(child.name) && joint.parent) joint.parent.attach(child)
        }
      }
      model.updateMatrixWorld(true)
      const endpoints = doors.find((door) => door.name === name)?.endpoints
      const mappedCenter = endpoints?.length === 2 ? rmfToThree({ x: (endpoints[0][0] + endpoints[1][0]) / 2, y: (endpoints[0][1] + endpoints[1][1]) / 2 }) : null
      return [{
        name,
        center: mappedCenter ? new THREE.Vector3(mappedCenter.x, mappedCenter.y, mappedCenter.z) : joints.reduce((point, { joint }) => point.add(joint.getWorldPosition(new THREE.Vector3())), new THREE.Vector3()).divideScalar(joints.length),
        joints: joints.map(({ side, joint }) => ({ joint, closed: joint.rotation.y, direction: side === 'left' ? -1 : 1 })),
        openness: 0,
      }]
    })
  }

  canMove(current, next) {
    return this.doors.every((door) => {
      const distance = Math.hypot(next.x - door.center.x, next.z - door.center.z)
      const previous = Math.hypot(current.x - door.center.x, current.z - door.center.z)
      if (distance < OPEN_DISTANCE) door.requested = true
      return door.openness >= 0.95 || distance >= 1.15 || distance > previous
    })
  }

  update(delta, robotPositions) {
    for (const door of this.doors) {
      const nearby = robotPositions.some((position) => position && Math.hypot(position.x - door.center.x, position.z - door.center.z) < OPEN_DISTANCE)
      const target = nearby || door.requested ? 1 : 0
      door.requested = false
      door.openness = THREE.MathUtils.lerp(door.openness, target, 1 - Math.exp(-Math.min(delta, 0.1) * 5))
      for (const { joint, closed, direction } of door.joints) joint.rotation.y = closed + direction * OPEN_ANGLE * door.openness
    }
  }

  dispose() {
    for (const door of this.doors) for (const { joint, closed } of door.joints) joint.rotation.y = closed
    this.doors = []
  }
}
