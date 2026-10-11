import * as THREE from 'three'
import { visualTokens } from '@/config/visualTokens.js'
import { rmfToThree } from '@/config/rmfMapTransform.js'

// One label per room, even when the RMF graph has multiple waypoints inside it.
const roomWaypoints = Object.freeze([
  ['Nurse Reception', ['reception_back']],
  ['Consultation Room 1', ['consult_1_1', 'consult_1_2']],
  ['Ward A', ['ward_a_1', 'ward_a_2']],
  ['Ward B', ['ward_b_1', 'ward_b_2']],
  ['Consultation Room 3', ['consult_3_1', 'consult_3_2']],
  ['Consultation Room 2', ['consult_2_1', 'consult_2_2']],
  ['Laboratory', ['lab']],
  ['Blood Draw', ['blood_draw']],
  ['X-Ray', ['x-ray']],
  ['Charging Station A', ['charging_station_1']],
  ['Charging Station B', ['charging_station_2']],
  ['Ultrasound', ['ultrasound_1', 'ultrasound_2']],
  ['ECG', ['ecg_1', 'ecg_2']],
  ['Therapy Room', ['therapy_room']],
  ['Waste Return', ['waste_return_1', 'waste_return_2']],
  ['Clothes Return', ['clothes_return_1', 'clothes_return_2']],
  ['Pharmacy', ['pharmacy']],
  ['Nurse Station', ['nurse_station']],
])
const additionalDoorRooms = Object.freeze({
  Pantry_room: 'Pantry', recycling_room: 'Recycling Room',
  restroom_men: "Men's Restroom", restroom_women: "Women's Restroom",
})

export function buildRoomLabels(data) {
  const byName = new Map(data.namedWaypoints.map((waypoint) => [waypoint.name, waypoint]))
  const labels = roomWaypoints.flatMap(([label, names]) => {
    const points = names.map((name) => byName.get(name)).filter(Boolean)
    if (!points.length) return []
    return [{ id: names[0], label, x: points.reduce((sum, point) => sum + point.x, 0) / points.length, y: points.reduce((sum, point) => sum + point.y, 0) / points.length }]
  })
  for (const door of data.doors) {
    const label = additionalDoorRooms[door.name]
    if (!label || !door.endpoints?.length) continue
    const [first, second] = door.endpoints
    labels.push({ id: door.name, label, x: (first[0] + second[0]) / 2, y: (first[1] + second[1]) / 2 })
  }
  return labels
}

export class RoomLabelLayer {
  constructor({ data, container, camera, canvas }) {
    this.camera = camera
    this.canvas = canvas
    this.visible = true
    this.suppressed = new Set()
    this.overlay = document.createElement('div')
    this.overlay.className = 'rmf-room-overlay'
    container.appendChild(this.overlay)
    this.entries = buildRoomLabels(data).map((room) => {
      const root = document.createElement('span')
      root.className = 'rmf-room-label'
      if (room.id.startsWith('charging_station_')) {
        root.style.setProperty('--room-label-color', visualTokens.chargingStation)
      }
      root.textContent = room.label
      this.overlay.appendChild(root)
      const point = rmfToThree(room)
      return { root, label: room.label, point: new THREE.Vector3(point.x, point.y + 0.6, point.z) }
    })
  }

  setVisible(visible) {
    this.visible = visible
    this.overlay.hidden = !visible
  }

  setSuppressedLabels(labels) { this.suppressed = new Set(labels) }

  update() {
    if (!this.visible) return
    const rect = this.canvas.getBoundingClientRect()
    const placed = []
    for (const entry of this.entries) {
      const point = entry.point.clone().project(this.camera)
      entry.root.hidden = this.suppressed.has(entry.label) || point.z < -1 || point.z > 1 || Math.abs(point.x) > 1 || Math.abs(point.y) > 1
      if (entry.root.hidden) continue
      const width = entry.root.offsetWidth
      const height = entry.root.offsetHeight
      const x = Math.max(width / 2, Math.min(rect.width - width / 2, (point.x * 0.5 + 0.5) * rect.width))
      const anchorY = (-point.y * 0.5 + 0.5) * rect.height
      // Search near the actual room instead of cascading down into other rooms.
      const step = height + 6
      const candidates = [0, -step, step].map((offset) => anchorY + offset)
      const y = candidates.find((candidate) => candidate >= height / 2 && candidate <= rect.height - height / 2 && !placed.some((other) => (
        Math.abs(other.x - x) < (other.width + width) / 2 + 6 && Math.abs(other.y - candidate) < (other.height + height) / 2 + 6
      ))) ?? anchorY
      placed.push({ x, y, width, height })
      entry.root.style.transform = `translate3d(${x}px, ${y}px, 0) translate(-50%, -50%)`
    }
  }

  dispose() { this.overlay.remove(); this.entries = [] }
}
