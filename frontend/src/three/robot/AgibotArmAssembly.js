import * as THREE from 'three'

const armLink = /^Link([1-7])_([lr])$/
const handLink = /^(left|right)_/i

export class AgibotArmAssembly {
  constructor(root) {
    this.root = root
    this.records = []
    this.assembledBounds = new THREE.Box3().setFromObject(root)
    root.updateMatrixWorld(true)

    const groups = new Map()
    root.traverse(mesh => {
      if (!mesh.isMesh) return
      const link = String(mesh.userData.source_link || mesh.name.replace(/_part_\d+$/, ''))
      const arm = armLink.exec(link)
      const hand = handLink.exec(link)
      if (!arm && !hand) return
      const side = arm ? arm[2] : hand[1].toLowerCase() === 'left' ? 'l' : 'r'
      const stage = arm ? Number(arm[1]) : 8
      const center = new THREE.Box3().setFromObject(mesh).getCenter(new THREE.Vector3())
      if (!groups.has(link)) groups.set(link, { side, stage, parts: [] })
      groups.get(link).parts.push({ mesh, center, original: mesh.position.clone() })
    })

    const centers = new Map()
    for (const [link, group] of groups) {
      const center = new THREE.Vector3()
      group.parts.forEach(part => center.add(part.center))
      centers.set(link, center.divideScalar(group.parts.length))
    }

    for (const side of ['l', 'r']) {
      const shoulder = centers.get(`Link1_${side}`)
      const wrist = centers.get(`Link7_${side}`)
      if (!shoulder || !wrist) continue
      const outward = wrist.clone().sub(shoulder).normalize()
      const perpendicular = new THREE.Vector3(0, 1, 0).cross(outward).normalize()
      const span = this.assembledBounds.getSize(new THREE.Vector3()).length()
      for (const [link, group] of groups) {
        if (group.side !== side) continue
        const groupCenter = centers.get(link)
        group.parts.forEach((part, index) => {
          const radial = part.center.clone().sub(groupCenter).addScaledVector(outward, -part.center.clone().sub(groupCenter).dot(outward))
          if (radial.lengthSq() < 1e-7) radial.copy(perpendicular).applyAxisAngle(outward, index * 2.39996)
          radial.normalize()
          const offsetWorld = outward.clone().multiplyScalar(span * .034 * group.stage)
            .addScaledVector(radial, span * .011 * (group.parts.length > 1 ? 1 : 0))
          const worldOrigin = part.mesh.getWorldPosition(new THREE.Vector3())
          const localEnd = part.mesh.parent.worldToLocal(worldOrigin.add(offsetWorld))
          this.records.push({ mesh: part.mesh, original: part.original, offset: localEnd.sub(part.original) })
        })
      }
    }

    this.set(1)
    this.explodedBounds = new THREE.Box3().setFromObject(root)
    this.set(0)
  }

  set(amount) {
    const value = THREE.MathUtils.clamp(amount, 0, 1)
    this.records.forEach(({ mesh, original, offset }) => {
      mesh.position.copy(original)
      if (value !== 0) mesh.position.addScaledVector(offset, value)
    })
    this.root.updateMatrixWorld(true)
  }

  boundsAt(amount) {
    const value = THREE.MathUtils.clamp(amount, 0, 1)
    return new THREE.Box3(
      this.assembledBounds.min.clone().lerp(this.explodedBounds.min, value),
      this.assembledBounds.max.clone().lerp(this.explodedBounds.max, value),
    )
  }
}
