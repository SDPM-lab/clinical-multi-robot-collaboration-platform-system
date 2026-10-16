import * as THREE from 'three'

const armLink = /^Link([1-7])_([lr])$/
const handLink = /^(left|right)_/i
const goldenAngle = 2.399963229728653
const keys = ['l', 'r', 'head', 'base']

export class AgibotArmAssembly {
  constructor(root) {
    this.root = root
    this.records = []
    root.updateMatrixWorld(true)
    this.assembledBounds = new THREE.Box3().setFromObject(root)

    const zones = { arms: [], head: [], base: [], mast: [] }
    root.traverse(mesh => {
      if (!mesh.isMesh) return
      const zone = mesh.userData.disassembly_zone
      if (zone in zones) zones[zone].push(mesh)
    })

    const centers = new Map()
    const armGroups = new Map()
    for (const mesh of zones.arms) {
      const link = String(mesh.userData.source_link || mesh.name.replace(/_part_\d+$/, ''))
      const arm = armLink.exec(link)
      const hand = handLink.exec(link)
      if (!arm && !hand) throw new Error(`Unrecognized AGIBOT arm link: ${link}`)
      const side = arm ? arm[2] : hand[1].toLowerCase() === 'left' ? 'l' : 'r'
      const stage = arm ? Number(arm[1]) : 8
      const center = new THREE.Box3().setFromObject(mesh).getCenter(new THREE.Vector3())
      if (!armGroups.has(link)) armGroups.set(link, { side, stage, parts: [] })
      armGroups.get(link).parts.push({ mesh, center })
    }
    for (const [link, group] of armGroups) {
      const center = new THREE.Vector3()
      group.parts.forEach(part => center.add(part.center))
      centers.set(link, center.divideScalar(group.parts.length))
    }

    const addRecord = (mesh, key, offsetWorld) => {
      const original = mesh.position.clone()
      const worldOrigin = mesh.getWorldPosition(new THREE.Vector3())
      const localEnd = mesh.parent.worldToLocal(worldOrigin.add(offsetWorld))
      this.records.push({ mesh, key, side: key === 'l' || key === 'r' ? key : null, original, offset: localEnd.sub(original) })
    }

    const fullSpan = this.assembledBounds.getSize(new THREE.Vector3()).length()
    for (const side of ['l', 'r']) {
      const shoulder = centers.get(`Link1_${side}`)
      const wrist = centers.get(`Link7_${side}`)
      if (!shoulder || !wrist) throw new Error(`AGIBOT ${side} arm shoulder or wrist missing`)
      const outward = wrist.clone().sub(shoulder).normalize()
      const perpendicular = new THREE.Vector3(0, 1, 0).cross(outward).normalize()
      for (const [link, group] of armGroups) {
        if (group.side !== side) continue
        const groupCenter = centers.get(link)
        group.parts.forEach((part, index) => {
          const radial = part.center.clone().sub(groupCenter)
          radial.addScaledVector(outward, -radial.dot(outward))
          if (radial.lengthSq() < 1e-7) radial.copy(perpendicular).applyAxisAngle(outward, index * goldenAngle)
          radial.normalize()
          const offsetWorld = outward.clone().multiplyScalar(fullSpan * .034 * group.stage)
            .addScaledVector(radial, fullSpan * .011 * (group.parts.length > 1 ? 1 : 0))
          addRecord(part.mesh, side, offsetWorld)
        })
      }
    }

    const zoneCenter = meshes => {
      const bounds = new THREE.Box3()
      meshes.forEach(mesh => bounds.expandByObject(mesh))
      return bounds.getCenter(new THREE.Vector3())
    }
    const vertical = zoneCenter(zones.head).sub(zoneCenter(zones.base)).normalize()
    const lateral = centers.get('Link7_r').clone().sub(centers.get('Link7_l')).normalize()
    const depth = new THREE.Vector3().crossVectors(vertical, lateral).normalize()

    for (const zone of ['head', 'base']) {
      const meshes = zones[zone]
      const bounds = new THREE.Box3()
      meshes.forEach(mesh => bounds.expandByObject(mesh))
      const center = bounds.getCenter(new THREE.Vector3())
      const span = bounds.getSize(new THREE.Vector3()).length()
      const groups = new Map()
      meshes.forEach(mesh => {
        const stem = mesh.name.replace(/_piece_\d+$/i, '')
        if (!groups.has(stem)) groups.set(stem, [])
        groups.get(stem).push(mesh)
      })
      const groupEntries = [...groups].sort(([a], [b]) => a.localeCompare(b))
      groupEntries.forEach(([, parts], groupIndex) => {
        const groupCenter = zoneCenter(parts)
        const groupRadial = groupCenter.clone().sub(center)
        groupRadial.addScaledVector(vertical, -groupRadial.dot(vertical))
        if (groupRadial.lengthSq() < 1e-7) groupRadial.copy(lateral).applyAxisAngle(vertical, groupIndex * goldenAngle)
        groupRadial.normalize()
        parts.forEach((mesh, index) => {
          const partCenter = new THREE.Box3().setFromObject(mesh).getCenter(new THREE.Vector3())
          const radial = partCenter.sub(groupCenter)
          radial.addScaledVector(vertical, -radial.dot(vertical))
          if (radial.lengthSq() < 1e-7) {
            const angle = index * goldenAngle
            radial.copy(lateral).multiplyScalar(Math.cos(angle)).addScaledVector(depth, Math.sin(angle))
          }
          radial.normalize()
          const offsetWorld = groupRadial.clone().multiplyScalar(span * .12)
            .addScaledVector(radial, span * .13)
            .addScaledVector(vertical, span * .09 * (groupIndex - (groupEntries.length - 1) / 2))
          addRecord(mesh, zone, offsetWorld)
        })
      })
    }

    this.set(1)
    this.explodedBounds = new THREE.Box3().setFromObject(root)
    this.set(0)
  }

  set(amount) {
    this.setZones(Object.fromEntries(keys.map(key => [key, amount])))
  }

  setSides(amounts) {
    this.setZones({ l: amounts.l, r: amounts.r, head: 0, base: 0 })
  }

  setZones(amounts) {
    this.records.forEach(({ mesh, key, original, offset }) => {
      const value = THREE.MathUtils.clamp(Number(amounts[key]) || 0, 0, 1)
      mesh.position.copy(original).addScaledVector(offset, value)
    })
    this.root.updateMatrixWorld(true)
  }

  zoneBounds(key) {
    const bounds = new THREE.Box3()
    this.records.forEach(({ mesh, key: recordKey }) => {
      if (recordKey === key) bounds.expandByObject(mesh)
    })
    return bounds
  }

  armBounds(side) { return this.zoneBounds(side) }

  boundsAt(amount) {
    const value = THREE.MathUtils.clamp(amount, 0, 1)
    return new THREE.Box3(
      this.assembledBounds.min.clone().lerp(this.explodedBounds.min, value),
      this.assembledBounds.max.clone().lerp(this.explodedBounds.max, value),
    )
  }
}
