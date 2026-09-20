import * as THREE from 'three'
import { rmfToThree } from '@/config/rmfMapTransform.js'
import { semanticColors, semanticTheme } from '@/config/robotVisualThemes.js'

const STATUS_COLORS = Object.freeze({ normal: 0x969892, active: 0x969892, emergency: semanticTheme.destinationHex, charging: semanticTheme.chargingStationHex })
export const ARRIVAL_THRESHOLD = 0.25
export const locationMarkerSize = Object.freeze({ normal: 0.52, destination: 0.66, activeDestination: 0.66, arrived: 0.74 })
export const destinationStyles = Object.freeze({
  idle: Object.freeze({ opacity: 0.14, emissiveIntensity: 0.05, scale: 1 }),
  approaching: Object.freeze({ opacity: 0.42, emissiveIntensity: 0.34, scale: 1.05 }),
  arrived: Object.freeze({ opacity: 0.96, emissiveIntensity: 0.9, scale: locationMarkerSize.arrived / locationMarkerSize.activeDestination }),
})

const makeStem = (color) => new THREE.Line(
  new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, 0.12, 0), new THREE.Vector3(0, 0.82, 0)]),
  new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.58 }),
)

const makeDestinationPin = () => {
  const pin = new THREE.Group()
  pin.name = 'Active Destination 3D Pin'
  const color = semanticTheme.destinationHex
  const material = new THREE.MeshStandardMaterial({
    color, emissive: color, emissiveIntensity: 0.22,
    transparent: true, opacity: 0.96, roughness: 0.42, metalness: 0.04, depthTest: false, depthWrite: false,
  })
  const ring = new THREE.Mesh(new THREE.TorusGeometry(0.11, 0.034, 10, 28), material.clone())
  ring.position.y = 0.1
  const center = new THREE.Mesh(
    new THREE.CircleGeometry(0.068, 24),
    new THREE.MeshBasicMaterial({ color: 0xfff7f2, transparent: true, opacity: 0.94, depthTest: false, depthWrite: false }),
  )
  center.position.set(0, 0.1, 0.006)
  const point = new THREE.Mesh(new THREE.ConeGeometry(0.09, 0.23, 20), material.clone())
  point.position.y = -0.08
  point.rotation.z = Math.PI
  const floorRing = new THREE.Mesh(
    new THREE.TorusGeometry(0.15, 0.022, 8, 28),
    new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: 0.65, transparent: true, opacity: 0.62, depthTest: false, depthWrite: false }),
  )
  floorRing.rotation.x = Math.PI / 2
  floorRing.position.y = -0.48
  pin.add(ring, center, point, floorRing)
  ;[ring, center, point, floorRing].forEach((object) => { object.renderOrder = 10 })
  pin.userData.materials = [ring.material, center.material, point.material, floorRing.material]
  pin.userData.baseScale = 1.32
  pin.scale.setScalar(pin.userData.baseScale)
  return pin
}

export class LocationMarkerLayer {
  constructor({ data, details, parent, container, camera, canvas, environmentGroup }) {
    this.data = data
    this.camera = camera
    this.canvas = canvas
    this.environmentGroup = environmentGroup
    this.visible = true
    this.labelsVisible = true
    this.raycaster = new THREE.Raycaster()
    this.entries = []
    this.retiringPins = []
    this.lastElapsed = null
    this.group = new THREE.Group()
    this.group.name = 'RMF Square Location Nodes'
    this.pinTransitionGroup = new THREE.Group()
    this.pinTransitionGroup.name = 'Destination Pin Transitions'
    parent.add(this.group, this.pinTransitionGroup)
    this.overlay = document.createElement('div')
    this.overlay.className = 'rmf-location-overlay'
    container.appendChild(this.overlay)
    this.setDetails(details)
  }

  setDetails(details) {
    this.entries.forEach((entry) => {
      if (!entry.pin) return
      entry.pin.removeFromParent()
      this.pinTransitionGroup.add(entry.pin)
      this.retiringPins.push({ pin: entry.pin, age: 0, opacities: entry.pin.userData.materials.map((material) => material.opacity) })
    })
    this.entries.forEach((entry) => entry.root.remove())
    this.group.traverse((object) => { object.geometry?.dispose(); object.material?.dispose() })
    this.group.clear()
    this.entries = []
    const visibleWaypoints = this.data.namedWaypoints.filter((waypoint) => details[waypoint.name])
    visibleWaypoints.forEach((waypoint, index) => this.addLocation(waypoint, details[waypoint.name], index, visibleWaypoints.length))
  }

  addLocation(waypoint, detail, sequenceIndex = 0, sequenceTotal = 1) {
    const transformed = rmfToThree(waypoint)
    const status = detail.statusKey || (waypoint.isCharger ? 'charging' : 'normal')
    const color = detail.color || STATUS_COLORS[status] || STATUS_COLORS.normal
    const baseOpacity = detail.isDestination ? destinationStyles.idle.opacity : detail.taskId ? 0.16 : 0.035
    const nodeWorld = new THREE.Vector3(transformed.x, transformed.y + 0.08, transformed.z)
    const anchorWorld = new THREE.Vector3(transformed.x, transformed.y + (detail.isDestination ? 1.12 : 0.9), transformed.z)
    const marker = new THREE.Group()
    const size = detail.isDestination ? locationMarkerSize.activeDestination : locationMarkerSize.normal
    const cube = new THREE.Mesh(
      new THREE.BoxGeometry(size, 0.06, size),
      new THREE.MeshStandardMaterial({
        color,
        emissive: color,
        emissiveIntensity: 0.08,
        transparent: true,
        opacity: baseOpacity,
        roughness: 0.5,
        metalness: 0,
        depthWrite: false,
      }),
    )
    const outline = new THREE.LineSegments(new THREE.EdgesGeometry(cube.geometry), new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.78 }))
    const stem = makeStem(color)
    cube.userData.baseOpacity = baseOpacity
    outline.userData.baseOpacity = 0.78
    stem.userData.baseOpacity = 0.58
    marker.add(cube, outline, stem)
    marker.position.copy(nodeWorld)
    const baseScale = detail.isDestination ? destinationStyles.idle.scale : detail.taskId ? 1.08 : 1
    marker.scale.setScalar(baseScale)
    marker.renderOrder = 7
    this.group.add(marker)
    const pin = detail.isDestination ? makeDestinationPin() : null
    if (pin) {
      pin.position.set(transformed.x, transformed.y + 0.55, transformed.z)
      pin.renderOrder = 9
      this.group.add(pin)
    }

    const root = document.createElement('div')
    root.className = `rmf-location${detail.taskId ? ' is-active' : ''}${status === 'charging' ? ' is-charging-station' : ''}`
    root.style.setProperty('--location-color', `#${color.toString(16).padStart(6, '0')}`)
    root.style.setProperty('--robot-color', detail.theme?.main || `#${color.toString(16).padStart(6, '0')}`)
    root.style.setProperty('--robot-soft', detail.theme?.soft || 'rgba(110, 108, 103, 0.12)')
    root.style.setProperty('--robot-glow', detail.theme?.glow || '#b5b2ab')
    root.style.setProperty('--success-color', semanticColors.success)
    root.innerHTML = `<strong>${detail.label}</strong>${detail.taskId ? `<small class="rmf-location__task">${detail.taskId} · ${detail.robot}</small>` : ''}<span class="rmf-location__success" aria-label="任務完成">✓</span>`
    this.overlay.appendChild(root)
    const entry = {
      detail,
      anchorWorld,
      nodeWorld,
      root,
      marker,
      cube,
      outline,
      stem,
      pin,
      pinBaseY: transformed.y + 0.55,
      pinFade: pin ? 0 : 1,
      baseScale,
      destinationState: 'idle',
      taskCompleted: false,
      priorityHidden: false,
      robotMatch: true,
      priorityMatch: true,
      screenPosition: null,
      entranceAge: 0,
      entranceDelay: sequenceTotal > 1 ? (sequenceIndex / (sequenceTotal - 1)) * 1.2 : 0,
      entranceProgress: 0,
    }
    this.entries.push(entry)
    this.applyEntryVisual(entry)
  }

  applyEntryVisual(entry) {
    const emphasis = entry.robotMatch && entry.priorityMatch ? 1 : 0.12
    const destinationStyle = entry.detail.isDestination
      ? destinationStyles[entry.destinationState]
      : null
    entry.cube.material.opacity = (destinationStyle?.opacity ?? entry.cube.userData.baseOpacity) * emphasis
    entry.cube.material.emissiveIntensity = destinationStyle?.emissiveIntensity ?? 0.08
    entry.outline.material.opacity = (entry.destinationState === 'arrived' ? 1 : entry.outline.userData.baseOpacity) * emphasis
    entry.stem.material.opacity = entry.stem.userData.baseOpacity * emphasis
    entry.marker.scale.setScalar(destinationStyle?.scale ?? entry.baseScale)
    if (entry.pin) {
      entry.pin.userData.materials.forEach((material, index) => {
        const isFloorRing = index === 3
        material.opacity = (entry.destinationState === 'arrived' ? (isFloorRing ? 0.88 : 1) : (isFloorRing ? 0.62 : 0.96)) * emphasis * entry.pinFade
        if ('emissiveIntensity' in material) material.emissiveIntensity = entry.destinationState === 'arrived' ? (isFloorRing ? 1.1 : 0.68) : (isFloorRing ? 0.65 : 0.22)
      })
      entry.pin.scale.setScalar(entry.pin.userData.baseScale * (entry.destinationState === 'arrived' ? 1.08 : 1))
    }
    entry.root.classList.toggle('is-approaching', entry.destinationState === 'approaching')
    entry.root.classList.toggle('is-arrived', entry.destinationState === 'arrived')
    entry.root.classList.toggle('is-completed', entry.taskCompleted)
    entry.root.style.opacity = String(entry.entranceProgress ?? 1)
  }

  setDestinationState(tasks, robotPositions, routeStates = new Map()) {
    const taskById = new Map(tasks.map((task) => [task.id, task]))
    this.entries.forEach((entry) => {
      if (!entry.detail.isDestination) return
      const task = taskById.get(entry.detail.taskId)
      const robotPosition = robotPositions.get(entry.detail.robotId)
      const routeState = routeStates.get(entry.detail.robotId)
      const distanceToDestination = robotPosition
        ? Math.hypot(robotPosition.x - entry.nodeWorld.x, robotPosition.z - entry.nodeWorld.z)
        : Infinity
      const arrived = distanceToDestination <= ARRIVAL_THRESHOLD && task?.status === 'arrived'
      const approaching = !arrived && task?.status === 'executing' && Boolean(
        routeState?.isFinalSegment
        || routeState?.progress >= 0.72
        || distanceToDestination <= 1.25,
      )
      const nextState = arrived ? 'arrived' : approaching ? 'approaching' : 'idle'
      const taskCompleted = task?.status === 'completed'
      if (nextState === entry.destinationState && taskCompleted === entry.taskCompleted) return
      entry.destinationState = nextState
      entry.taskCompleted = taskCompleted
      this.applyEntryVisual(entry)
    })
  }

  setArrivalState(tasks, robotPositions) {
    this.setDestinationState(tasks, robotPositions)
  }

  setVisible(visible) { this.visible = visible; this.group.visible = visible; this.pinTransitionGroup.visible = visible; this.overlay.hidden = !visible }
  setLabelsVisible(visible) { this.labelsVisible = visible; this.overlay.style.display = visible ? '' : 'none' }
  setSelectedRobot(robotId = null) {
    this.entries.forEach((entry) => {
      const selected = !robotId || entry.detail.robotId === robotId
      entry.robotMatch = selected
      entry.root.classList.toggle('is-dimmed', !(entry.robotMatch && entry.priorityMatch))
      this.applyEntryVisual(entry)
    })
  }

  setPriorityFilter(priorities, isolate = false) {
    const selected = new Set(priorities)
    this.entries.forEach((entry) => {
      const match = !entry.detail.priority || selected.has(entry.detail.priority)
      entry.priorityMatch = match
      entry.root.classList.toggle('is-dimmed', !(entry.robotMatch && entry.priorityMatch))
      entry.priorityHidden = isolate && !match
      entry.root.hidden = entry.priorityHidden
      entry.marker.visible = !(isolate && !match)
      if (entry.pin) entry.pin.visible = !(isolate && !match)
      this.applyEntryVisual(entry)
    })
  }

  getRobotLabelScreenPosition(robotId) {
    const candidates = this.entries.filter((entry) => (
      entry.detail.robotId === robotId
      && entry.detail.taskId
      && !entry.root.hidden
      && entry.screenPosition
    ))
    const destination = candidates.find((entry) => entry.detail.isDestination)
    return (destination || candidates[0])?.screenPosition || null
  }

  update(elapsed = 0) {
    if (!this.visible) return
    const delta = this.lastElapsed == null ? 0 : Math.min(Math.max(elapsed - this.lastElapsed, 0), 0.1)
    this.lastElapsed = elapsed
    this.retiringPins = this.retiringPins.filter((retiring) => {
      retiring.age += delta
      const fade = Math.max(0, 1 - retiring.age / 0.22)
      retiring.pin.userData.materials.forEach((material, index) => { material.opacity = retiring.opacities[index] * fade })
      if (fade > 0) return true
      retiring.pin.removeFromParent()
      retiring.pin.traverse((object) => { object.geometry?.dispose(); object.material?.dispose() })
      return false
    })
    const rect = this.canvas.getBoundingClientRect()
    const cameraPosition = this.camera.getWorldPosition(new THREE.Vector3())
    const visibleEntries = []
    this.entries.forEach((entry) => {
      if (entry.entranceProgress < 1) {
        entry.entranceAge += delta
        const raw = Math.max(0, Math.min(1, (entry.entranceAge - entry.entranceDelay) / 0.5))
        entry.entranceProgress = 1 - ((1 - raw) ** 3)
        this.applyEntryVisual(entry)
      }
      if (entry.pin) {
        entry.pinFade = Math.min(1, entry.pinFade + delta / 0.22)
        entry.pin.position.y = entry.pinBaseY + Math.sin(elapsed * 1.7 + entry.nodeWorld.x) * 0.025
        entry.pin.lookAt(cameraPosition.x, entry.pin.position.y, cameraPosition.z)
        this.applyEntryVisual(entry)
      }
      if (entry.destinationState === 'approaching') {
        entry.marker.scale.setScalar(destinationStyles.approaching.scale * (1 + Math.sin(elapsed * 3) * 0.025))
      }
      entry.screenPosition = null
      if (!this.labelsVisible) { entry.root.hidden = true; return }
      const projected = entry.anchorWorld.clone().project(this.camera)
      const outside = projected.z < -1 || projected.z > 1 || Math.abs(projected.x) > 1.04 || Math.abs(projected.y) > 1.04
      const direction = entry.anchorWorld.clone().sub(cameraPosition)
      const distance = direction.length()
      this.raycaster.set(cameraPosition, direction.normalize())
      const intersection = this.raycaster.intersectObject(this.environmentGroup, true)[0]
      const occluded = intersection && intersection.distance < distance - 0.45
      entry.root.hidden = entry.priorityHidden || outside || occluded
      if (!entry.root.hidden) visibleEntries.push({ entry, x: (projected.x * 0.5 + 0.5) * rect.width, y: (-projected.y * 0.5 + 0.5) * rect.height })
    })
    visibleEntries.sort((a, b) => a.y - b.y)
    const placed = []
    visibleEntries.forEach((item) => {
      let y = item.y
      for (let attempt = 0; attempt < 5; attempt += 1) {
        if (!placed.some((other) => Math.abs(other.x - item.x) < 96 && Math.abs(other.y - y) < 30)) break
        y -= 24
      }
      placed.push({ x: item.x, y })
      item.entry.screenPosition = { x: item.x, y, height: item.entry.root.offsetHeight }
      item.entry.root.style.transform = `translate3d(${item.x}px, ${y}px, 0) translate(-50%, -100%)`
    })
  }

  dispose() {
    this.overlay.remove()
    this.group.removeFromParent()
    this.pinTransitionGroup.removeFromParent()
    this.group.traverse((object) => { object.geometry?.dispose(); object.material?.dispose() })
    this.pinTransitionGroup.traverse((object) => { object.geometry?.dispose(); object.material?.dispose() })
    this.entries = []
    this.retiringPins = []
  }
}
