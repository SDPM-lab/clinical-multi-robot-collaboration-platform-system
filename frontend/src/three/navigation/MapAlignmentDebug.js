import * as THREE from 'three'

const solveSimilarity = (pairs, invertX, invertY) => {
  const source = pairs.map(({ rmf }) => ({ x: invertX ? -rmf.x : rmf.x, y: invertY ? -rmf.y : rmf.y }))
  const target = pairs.map(({ world }) => ({ x: world.x, y: world.z }))
  const mean = (points, key) => points.reduce((sum, point) => sum + point[key], 0) / points.length
  const sx = mean(source, 'x'); const sy = mean(source, 'y')
  const tx = mean(target, 'x'); const ty = mean(target, 'y')
  let dot = 0; let cross = 0; let norm = 0
  source.forEach((point, index) => {
    const ax = point.x - sx; const ay = point.y - sy
    const bx = target[index].x - tx; const by = target[index].y - ty
    dot += ax * bx + ay * by
    cross += ax * by - ay * bx
    norm += ax * ax + ay * ay
  })
  const rotation = Math.atan2(cross, dot)
  const scale = Math.hypot(dot, cross) / Math.max(norm, 1e-9)
  const cos = Math.cos(rotation); const sin = Math.sin(rotation)
  const offsetX = tx - scale * (sx * cos - sy * sin)
  const offsetZ = ty - scale * (sx * sin + sy * cos)
  const error = source.reduce((sum, point, index) => {
    const x = scale * (point.x * cos - point.y * sin) + offsetX
    const z = scale * (point.x * sin + point.y * cos) + offsetZ
    return sum + Math.hypot(x - target[index].x, z - target[index].y) ** 2
  }, 0)
  return { scale, rotation, offsetX, offsetZ, invertX, invertY, floorY: 0, rmsError: Math.sqrt(error / pairs.length) }
}

export class MapAlignmentDebug {
  constructor({ camera, canvas, environmentGroup, scene, vertices, selectedId }) {
    this.camera = camera
    this.canvas = canvas
    this.environmentGroup = environmentGroup
    this.scene = scene
    this.vertices = new Map(vertices.map((vertex) => [vertex.id, vertex]))
    this.selectedId = selectedId
    this.pairs = []
    this.markers = []
    this.raycaster = new THREE.Raycaster()
    this.pointer = new THREE.Vector2()
    this.onPointerDown = this.onPointerDown.bind(this)
    canvas.addEventListener('pointerdown', this.onPointerDown)
  }

  setSelectedId(id) { this.selectedId = id }

  onPointerDown(event) {
    const vertex = this.vertices.get(this.selectedId)
    if (!vertex) return
    const rect = this.canvas.getBoundingClientRect()
    this.pointer.set(((event.clientX - rect.left) / rect.width) * 2 - 1, -((event.clientY - rect.top) / rect.height) * 2 + 1)
    this.raycaster.setFromCamera(this.pointer, this.camera)
    const intersections = this.raycaster.intersectObject(this.environmentGroup, true)
    const hit = intersections.find((intersection) => (
      intersection.face
      && intersection.face.normal.clone().transformDirection(intersection.object.matrixWorld).y > 0.45
    ))
    const selectedHit = hit
    if (!selectedHit) return
    this.pairs = this.pairs.filter((pair) => pair.id !== vertex.id)
    this.pairs.push({ id: vertex.id, rmf: { x: vertex.x, y: vertex.y }, world: selectedHit.point.clone() })
    const marker = new THREE.Mesh(new THREE.SphereGeometry(0.12, 12, 8), new THREE.MeshBasicMaterial({ color: 0xdc925d }))
    marker.position.copy(selectedHit.point).add(new THREE.Vector3(0, 0.08, 0))
    this.scene.add(marker); this.markers.push(marker)
    console.table(this.pairs.map((pair) => ({ vertex: pair.id, rmfX: pair.rmf.x, rmfY: pair.rmf.y, worldX: pair.world.x, worldZ: pair.world.z })))
    if (this.pairs.length >= 3) {
      const candidates = [[false, false], [false, true], [true, false], [true, true]].map(([x, y]) => solveSimilarity(this.pairs, x, y)).sort((a, b) => a.rmsError - b.rmsError)
      console.log('RMF_MAP_TRANSFORM_CANDIDATE', JSON.stringify(candidates[0], null, 2))
    }
  }

  dispose() {
    this.canvas.removeEventListener('pointerdown', this.onPointerDown)
    this.markers.forEach((marker) => { marker.removeFromParent(); marker.geometry.dispose(); marker.material.dispose() })
    this.markers = []
  }
}
