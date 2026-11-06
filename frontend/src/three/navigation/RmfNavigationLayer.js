import * as THREE from 'three'
import { visualTokens, colorHex } from '@/config/visualTokens.js'
import { rmfToThree } from '@/config/rmfMapTransform.js'
import { overviewRouteColors, robotRouteColors, routeLayerY, routeVisualConfig } from '@/data/demoActiveRoutes.js'
import { RobotRouteController } from './RobotRouteController.js'

const BASE_COLOR = 0xDAC9A6
const UP = new THREE.Vector3(0, 1, 0)

export const routeStyle = Object.freeze({
  baseRouteRadius: routeVisualConfig.baseRouteRadius,
  activeRouteRadius: routeVisualConfig.activeRouteRadius,
  selectedRouteRadius: routeVisualConfig.selectedRouteRadius,
})

const pointOf = (vertex, height = routeVisualConfig.routeHeight) => {
  const point = rmfToThree(vertex)
  return new THREE.Vector3(point.x, point.y + height, point.z)
}
const atHeight = (point, height) => point.clone().setY(height)

const segment = (start, end, radius, color, opacity, renderOrder) => {
  const direction = end.clone().sub(start)
  const length = direction.length()
  if (length < 0.001) return null
  const material = new THREE.MeshBasicMaterial({ color, transparent: true, opacity, depthTest: true, depthWrite: false })
  material.userData.baseOpacity = opacity
  const mesh = new THREE.Mesh(new THREE.CylinderGeometry(radius, radius, length, 12, 1), material)
  mesh.position.copy(start).add(end).multiplyScalar(0.5)
  mesh.quaternion.setFromUnitVectors(UP, direction.normalize())
  mesh.renderOrder = renderOrder
  mesh.userData.isRouteTube = true
  return mesh
}

const ribbonMaterial = (color, opacity) => {
  const material = new THREE.MeshBasicMaterial({ color, transparent: true, opacity, blending: THREE.NormalBlending, depthTest: true, depthWrite: false })
  material.userData.baseOpacity = opacity
  return material
}

const ribbonSegment = (start, end, width, color, opacity, renderOrder) => {
  const direction = end.clone().sub(start)
  direction.y = 0
  const length = direction.length()
  if (length < 0.001) return null
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(width, 0.012, length), ribbonMaterial(color, opacity))
  mesh.position.copy(start).add(end).multiplyScalar(0.5)
  mesh.rotation.y = Math.atan2(direction.x, direction.z)
  mesh.renderOrder = renderOrder
  mesh.userData.isRouteRibbon = true
  return mesh
}

const ribbonJoin = (point, width, color, opacity, renderOrder) => {
  const mesh = new THREE.Mesh(new THREE.CircleGeometry(width * 0.5, 18), ribbonMaterial(color, opacity))
  mesh.rotation.x = -Math.PI / 2
  mesh.position.copy(point)
  mesh.renderOrder = renderOrder
  mesh.userData.isRouteRibbonJoin = true
  return mesh
}

const chevronGeometry = (length, width) => {
  const thickness = width * 0.19
  const shape = new THREE.Shape()
  shape.moveTo(-width / 2, -length / 2)
  shape.lineTo(0, length / 2)
  shape.lineTo(width / 2, -length / 2)
  shape.lineTo(width / 2 - thickness, -length / 2)
  shape.lineTo(0, length / 2 - thickness * 1.7)
  shape.lineTo(-width / 2 + thickness, -length / 2)
  shape.closePath()
  const geometry = new THREE.ShapeGeometry(shape)
  geometry.rotateX(-Math.PI / 2)
  geometry.rotateY(Math.PI)
  return geometry
}

const addRibbon = (group, start, end, width, color, opacity, renderOrder, addStartJoin = false) => {
  const band = ribbonSegment(start, end, width, color, opacity, renderOrder)
  if (band) group.add(band)
  if (addStartJoin) group.add(ribbonJoin(start, width, color, opacity, renderOrder))
  group.add(ribbonJoin(end, width, color, opacity, renderOrder))
}

const metrics = (points) => {
  const lengths = points.slice(1).map((point, index) => point.distanceTo(points[index]))
  return { lengths, total: lengths.reduce((sum, length) => sum + length, 0) }
}

const sample = (points, distance) => {
  const { lengths, total } = metrics(points)
  let remaining = THREE.MathUtils.euclideanModulo(distance, total || 1)
  for (let index = 0; index < lengths.length; index += 1) {
    const tangent = points[index + 1].clone().sub(points[index]).normalize()
    if (remaining <= lengths[index]) return { point: points[index].clone().addScaledVector(tangent, remaining), tangent }
    remaining -= lengths[index]
  }
  return { point: points.at(-1).clone(), tangent: points.at(-1).clone().sub(points.at(-2)).normalize() }
}

const emphasize = (group, factor) => group.traverse((object) => {
  if (!object.material) return
  const materials = Array.isArray(object.material) ? object.material : [object.material]
  materials.forEach((material) => {
    if (material.userData.baseOpacity == null) material.userData.baseOpacity = material.opacity
    material.userData.emphasisFactor = factor
    material.transparent = true
    material.opacity = material.userData.baseOpacity * factor
  })
})

const setRouteScale = (entry, selected) => {
  const widthScale = selected ? routeVisualConfig.selectedRouteRadius / routeVisualConfig.activeRouteRadius : 1
  for (const group of [entry.activeRouteGroup, entry.completedRouteGroup]) {
    group.traverse((object) => {
      if (object.userData.isRouteRibbon) object.scale.set(widthScale, 1, 1)
      if (object.userData.isRouteRibbonJoin) object.scale.set(widthScale, widthScale, 1)
    })
  }
  entry.arrows.forEach((arrow) => arrow.scale.setScalar(selected ? 1.2 : 1))
}

export class RmfNavigationLayer {
  constructor({ data, parent, routes = [], robots = [], robotWaypoints = {}, camera, overview = false, showRobotModels = true }) {
    this.data = data
    this.camera = camera
    this.overview = overview
    this.showRobotModels = showRobotModels
    this.vertices = new Map(data.vertices.map((vertex) => [vertex.id, vertex]))
    this.group = new THREE.Group(); this.group.name = overview ? 'Overview Highest Priority Route' : 'RMF Navigation Graph'
    this.baseGroup = new THREE.Group(); this.baseGroup.name = 'baseNavigationLayer'
    this.activeGroup = new THREE.Group(); this.activeGroup.name = 'activeRouteLayer'
    this.completedGroup = new THREE.Group(); this.completedGroup.name = 'completedRouteLayer'
    this.previewGroup = new THREE.Group(); this.previewGroup.name = 'previewRouteLayer'
    this.robotGroup = new THREE.Group(); this.robotGroup.name = 'realtimeRobotLayer'
    this.group.add(this.baseGroup, this.activeGroup, this.completedGroup, this.previewGroup, this.robotGroup)
    parent.add(this.group)
    this.routes = routes
    this.robots = robots
    this.robotWaypoints = robotWaypoints
    this.routeEntries = []
    this.robotControllers = new Map()
    this.flowDistance = 0
    this.selectedRobotId = null
    this.followRobotId = null
    this.priorityFilter = new Set(['emergency', 'high', 'normal', 'low'])
    this.isolatePriorities = false
    this.arrowsVisible = true
    this.elapsed = 0
    this.buildBaseGraph()
    this.setRoutes(routes)
  }

  buildBaseGraph() {
    if (this.overview) { this.baseGroup.visible = false; return }
    const seen = new Set()
    this.data.lanes.forEach((lane) => {
      const key = [lane.from, lane.to].sort().join(':')
      if (seen.has(key)) return
      seen.add(key)
      const from = this.vertices.get(lane.from)
      const to = this.vertices.get(lane.to)
      if (!from || !to) return
      const line = segment(pointOf(from, routeVisualConfig.baseHeight), pointOf(to, routeVisualConfig.baseHeight), routeVisualConfig.baseRouteRadius, BASE_COLOR, 0.24, 1)
      if (line) this.baseGroup.add(line)
    })
  }

  setRoutes(routes) {
    this.disposeVisualGroup(this.activeGroup); this.activeGroup.clear()
    this.disposeVisualGroup(this.completedGroup); this.completedGroup.clear()
    this.robotControllers.forEach((controller) => controller.dispose())
    this.robotControllers.clear()
    this.routeEntries = []
    const routedRobots = new Set()

    routes.forEach((route) => {
      const points = route.vertexIds.map((id) => this.vertices.get(id)).filter(Boolean).map((vertex) => pointOf(vertex))
      if (points.length < 2) return
      routedRobots.add(route.robotId)
      const robotColors = route.colors || robotRouteColors[route.robotId] || robotRouteColors.R04
      const colors = this.overview
        ? { main: overviewRouteColors.pending, completed: overviewRouteColors.completed, arrow: overviewRouteColors.arrow }
        : { main: robotColors.main, completed: robotColors.completed, arrow: robotColors.arrow }
      const activeRouteGroup = new THREE.Group(); activeRouteGroup.name = `${route.taskId} Active Route`
      const completedRouteGroup = new THREE.Group(); completedRouteGroup.name = `${route.taskId} Completed Route`
      const arrowGroup = new THREE.Group(); arrowGroup.name = `${route.taskId} Direction Arrows`
      this.activeGroup.add(activeRouteGroup, arrowGroup)
      this.completedGroup.add(completedRouteGroup)

      const { lengths, total } = metrics(points)
      const robotRouteOffset = this.overview ? 0 : routeLayerY[route.robotId] || 0
      const activeHeight = routeVisualConfig.routeHeight + robotRouteOffset
      const completedHeight = routeVisualConfig.completedHeight + robotRouteOffset
      const arrowHeight = routeVisualConfig.arrowHeight + robotRouteOffset
      let completedDistance = total * THREE.MathUtils.clamp(route.progress, 0, 1)
      lengths.forEach((length, index) => {
        const start = points[index]
        const end = points[index + 1]
        addRibbon(
          activeRouteGroup,
          atHeight(start, activeHeight),
          atHeight(end, activeHeight),
          routeVisualConfig.width,
          colors.main,
          routeVisualConfig.opacity,
          2,
          index === 0,
        )
        if (completedDistance >= length) {
          addRibbon(completedRouteGroup, atHeight(start, completedHeight), atHeight(end, completedHeight), routeVisualConfig.width, colors.completed, 0.86, 3, index === 0)
          completedDistance -= length
        } else if (completedDistance > 0) {
          const split = start.clone().lerp(end, completedDistance / length)
          addRibbon(completedRouteGroup, atHeight(start, completedHeight), atHeight(split, completedHeight), routeVisualConfig.width, colors.completed, 0.86, 3, index === 0)
          completedDistance = 0
        }
      })

      const arrowCount = Math.max(1, Math.floor(total / routeVisualConfig.arrowSpacing))
      const arrows = []
      for (let index = 0; index < arrowCount; index += 1) {
        const arrowColor = new THREE.Color(visualTokens.white).lerp(new THREE.Color(colors.arrow), 0.35)
        const material = new THREE.MeshBasicMaterial({ color: arrowColor, transparent: true, opacity: 0.82, blending: THREE.NormalBlending, depthTest: true, depthWrite: false, side: THREE.DoubleSide })
        material.userData.baseOpacity = 0.82
        const arrow = new THREE.Mesh(chevronGeometry(routeVisualConfig.arrowLength, routeVisualConfig.arrowWidth), material)
        arrow.userData.offset = (index + 0.5) * routeVisualConfig.arrowSpacing
        const pose = sample(points, arrow.userData.offset)
        arrow.position.copy(pose.point).setY(arrowHeight)
        arrow.userData.height = arrowHeight
        arrow.rotation.y = Math.atan2(pose.tangent.x, pose.tangent.z)
        arrow.renderOrder = 4
        arrowGroup.add(arrow)
        arrows.push(arrow)
      }
      const revealObjects = []
      ;[activeRouteGroup, completedRouteGroup, arrowGroup].forEach((group) => group.traverse((object) => {
        if (object.material) revealObjects.push(object)
      }))
      revealObjects.forEach((object, index) => { object.userData.routeRevealOffset = index / Math.max(1, revealObjects.length - 1) })
      this.routeEntries.push({ route, points, total, activeRouteGroup, completedRouteGroup, arrowGroup, arrows, revealObjects, entranceAge: 0 })
      if (this.showRobotModels) this.addRobotController(route.robotId, points, route.progress, colors.main)
    })

    if (this.showRobotModels) this.robots.forEach((robot) => {
      if (routedRobots.has(robot.id)) return
      const waypoint = this.data.namedWaypoints.find((entry) => entry.name === this.robotWaypoints[robot.id])
      if (!waypoint) return
      this.addRobotController(robot.id, [pointOf(waypoint, 0)], 0, (robotRouteColors[robot.id] || robotRouteColors.R04).main)
    })
    this.applyEmphasis()
  }

  addRobotController(id, points, progress, color) {
    const robot = this.robots.find((entry) => entry.id === id)
    const controller = new RobotRouteController({
      id,
      parent: this.robotGroup,
      points,
      progress,
      color,
      offline: robot?.state === 'offline',
      modelAssetKey: robot?.modelAssetKey,
    })
    this.robotControllers.set(id, controller)
    controller.load().catch((error) => console.error(`${id} robot model load failed:`, error))
  }

  applyEmphasis() {
    this.routeEntries.forEach((entry) => {
      const priorityMatch = this.priorityFilter.has(entry.route.priority)
      const robotMatch = !this.selectedRobotId || entry.route.robotId === this.selectedRobotId
      const factor = robotMatch && priorityMatch ? 1 : this.isolatePriorities && !priorityMatch ? 0 : 0.12
      for (const group of [entry.activeRouteGroup, entry.completedRouteGroup, entry.arrowGroup]) {
        group.visible = factor > 0
        emphasize(group, factor || 0)
      }
      setRouteScale(entry, Boolean(this.selectedRobotId && entry.route.robotId === this.selectedRobotId))
    })
    this.robotControllers.forEach((controller, id) => {
      const route = this.routeEntries.find((entry) => entry.route.robotId === id)?.route
      const priorityMatch = !route || this.priorityFilter.has(route.priority)
      const robotMatch = !this.selectedRobotId || id === this.selectedRobotId
      const factor = robotMatch && priorityMatch ? 1 : this.isolatePriorities && !priorityMatch ? 0 : 0.12
      controller.setEmphasis(factor)
      controller.setSelected(Boolean(this.selectedRobotId && id === this.selectedRobotId))
      controller.setFollowing(id === this.followRobotId)
    })
  }

  update(delta) {
    this.elapsed += delta
    this.flowDistance += delta * routeVisualConfig.arrowFlowSpeed
    this.routeEntries.forEach((entry) => {
      const { points, arrows, arrowGroup, revealObjects } = entry
      if (entry.entranceAge < 3.2) {
        entry.entranceAge = Math.min(3.2, entry.entranceAge + delta)
        const overall = entry.entranceAge / 3.2
        revealObjects.forEach((object) => {
          const local = THREE.MathUtils.smoothstep(overall, object.userData.routeRevealOffset * 0.72, object.userData.routeRevealOffset * 0.72 + 0.28)
          const materials = Array.isArray(object.material) ? object.material : [object.material]
          materials.forEach((material) => {
            material.opacity = material.userData.baseOpacity * (material.userData.emphasisFactor ?? 1) * local
          })
        })
      }
      if (!arrowGroup.visible) return
      arrows.forEach((arrow) => {
        const pose = sample(points, this.flowDistance + arrow.userData.offset)
        arrow.position.copy(pose.point).setY(arrow.userData.height)
        arrow.rotation.y = Math.atan2(pose.tangent.x, pose.tangent.z)
        arrow.visible = this.arrowsVisible
      })
    })
    this.robotControllers.forEach((controller) => controller.update(delta, this.camera, this.elapsed, this.doorController))
  }

  setSelectedRobot(id = null) { this.selectedRobotId = id; this.applyEmphasis() }
  setFollowingRobot(id = null) { this.followRobotId = id; this.applyEmphasis() }
  setPreviewRoute(route) {
    this.disposeVisualGroup(this.previewGroup); this.previewGroup.clear()
    if (!route) return
    const points = route.vertexIds.map((id) => this.vertices.get(id)).filter(Boolean).map((vertex) => pointOf(vertex, 0.075))
    if (points.length < 2) return
    const geometry = new THREE.BufferGeometry().setFromPoints(points)
    const material = new THREE.LineDashedMaterial({ color: route.colors?.main || robotRouteColors[route.robotId]?.main || colorHex(visualTokens.neutral), dashSize: 0.34, gapSize: 0.2, transparent: true, opacity: 0.72, depthTest: true })
    const line = new THREE.Line(geometry, material)
    line.computeLineDistances(); line.renderOrder = 4; this.previewGroup.add(line)
  }
  setPriorityFilter(priorities, isolate = false) { this.priorityFilter = new Set(priorities); this.isolatePriorities = isolate; this.applyEmphasis() }
  getRobotPosition(id) { return this.robotControllers.get(id)?.getWorldPosition() || null }
  getRobotInfoAnchor(id) { return this.robotControllers.get(id)?.getInfoAnchor() || null }
  getRobotForward(id) { return this.robotControllers.get(id)?.getForwardVector() || null }
  getRobotRouteState(id) { return this.robotControllers.get(id)?.getRouteState() || null }
  getRobotPickables() { return [...this.robotControllers.values()].flatMap((controller) => controller.getPickables()) }
  getRoute(id) { return this.routeEntries.find((entry) => entry.route.robotId === id)?.route || null }
  setBaseVisible(value) { this.baseGroup.visible = value }
  setActiveVisible(value) { this.activeGroup.visible = value; this.completedGroup.visible = value }
  setRobotsVisible(value) { this.robotGroup.visible = value }
  setArrowsVisible(value) {
    this.arrowsVisible = value
    this.routeEntries.forEach((entry) => {
      entry.arrows.forEach((arrow) => { arrow.visible = value })
    })
  }
  disposeVisualGroup(group) {
    group.traverse((object) => {
      object.geometry?.dispose()
      const materials = Array.isArray(object.material) ? object.material : [object.material]
      materials.filter(Boolean).forEach((material) => material.dispose())
    })
  }
  dispose() {
    this.robotControllers.forEach((controller) => controller.dispose())
    this.robotControllers.clear()
    this.group.removeFromParent()
    this.disposeVisualGroup(this.baseGroup)
    this.disposeVisualGroup(this.activeGroup)
    this.disposeVisualGroup(this.completedGroup)
    this.disposeVisualGroup(this.previewGroup)
    this.group.clear()
  }
}

export const navigationColors = Object.freeze({ base: BASE_COLOR, ...overviewRouteColors })
