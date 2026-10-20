import * as THREE from 'three'

const armLink = /^Link([1-7])_([lr])$/
const handLink = /^(left|right)_/i
const down = new THREE.Vector3(0, -1, 0)
const parkedAngle = THREE.MathUtils.degToRad(60)

// Pose only the cloned realtime-map model. Robot Status keeps the original T-pose for disassembly.
export function poseAgibotMapArms(model) {
  const root = model.getObjectByName('AGIBOT_A2D')
  if (!root) return false
  model.updateMatrixWorld(true)
  const sides = {
    l: { nodes: new Set(), shoulder: new THREE.Box3(), wrist: new THREE.Box3() },
    r: { nodes: new Set(), shoulder: new THREE.Box3(), wrist: new THREE.Box3() },
  }

  root.traverse(mesh => {
    if (!mesh.isMesh || mesh.userData.disassembly_zone !== 'arms') return
    const link = String(mesh.userData.source_link || mesh.name.replace(/_part_\d+$/, ''))
    const arm = armLink.exec(link)
    const hand = handLink.exec(link)
    const side = arm?.[2] || (hand?.[1].toLowerCase() === 'left' ? 'l' : hand ? 'r' : null)
    if (!side) return
    let group = mesh
    while (group.parent && group.parent !== root) group = group.parent
    if (group.parent !== root) return
    sides[side].nodes.add(group)
    if (arm?.[1] === '1') sides[side].shoulder.expandByObject(mesh)
    if (arm?.[1] === '7') sides[side].wrist.expandByObject(mesh)
  })

  if (Object.values(sides).some(side => !side.nodes.size || side.shoulder.isEmpty() || side.wrist.isEmpty())) return false

  for (const [name, side] of Object.entries(sides)) {
    const shoulder = root.worldToLocal(side.shoulder.getCenter(new THREE.Vector3()))
    const wrist = root.worldToLocal(side.wrist.getCenter(new THREE.Vector3()))
    const outward = wrist.sub(shoulder).normalize()
    const axis = outward.clone().cross(down).normalize()
    if (axis.lengthSq() < 0.5) return false
    const pivot = new THREE.Group()
    pivot.name = `${name === 'l' ? 'Left' : 'Right'} parked arm pivot`
    pivot.position.copy(shoulder)
    root.add(pivot)
    root.updateMatrixWorld(true)
    for (const group of side.nodes) pivot.attach(group)
    pivot.quaternion.setFromAxisAngle(axis, parkedAngle)
    root.updateMatrixWorld(true)
  }
  return true
}
