import { describe, expect, it } from 'vitest'
import navigation from '../public/generated/rmf-navigation.json'
import * as THREE from 'three'
import { rmfMapTransform, rmfToThree } from '../src/config/rmfMapTransform.js'
import { buildActiveRoutes, buildLocationDetails, robotRouteColors, routeLayerY, routeVisualConfig, sortTasksByPriority } from '../src/data/demoActiveRoutes.js'
import { LocationMarkerLayer } from '../src/three/navigation/LocationMarkerLayer.js'
import { REALTIME_ROBOT_SCALE_MULTIPLIER, ROBOT_HIT_TARGET } from '../src/three/navigation/RobotRouteController.js'
import { RmfNavigationLayer } from '../src/three/navigation/RmfNavigationLayer.js'
import { robotVisualThemes, semanticColors } from '../src/config/robotVisualThemes.js'

describe('RMF navigation data', () => {
  it('sorts task copies by priority, start time, then id and defaults missing priority to normal', () => {
    const source = [
      { id: 'T004', priority: 'low', startTime: '08:00:00' },
      { id: 'T003', priority: 'high', startTime: '09:30:00' },
      { id: 'T002', startTime: '08:30:00' },
      { id: 'T001', priority: 'high', startTime: '09:30:00' },
      { id: 'T005', priority: 'normal', startTime: '10:00:00' },
    ]
    expect(sortTasksByPriority(source).map((task) => task.id)).toEqual(['T001', 'T003', 'T002', 'T005', 'T004'])
    expect(source.map((task) => task.id)).toEqual(['T004', 'T003', 'T002', 'T001', 'T005'])
  })

  it('contains the authoritative L1 graph and named charging waypoint', () => {
    expect(navigation.sourceBuilding).toBe('ros2_ws/src/my_hospital_rmf/maps/L1.building.yaml')
    expect(navigation.sourceNavigationGraph).toBe('ros2_ws/src/my_hospital_rmf/nav_graphs_generated/0.yaml')
    expect(navigation.levels.map((level) => level.id)).toEqual(['L1'])
    expect(navigation.vertices).toHaveLength(46)
    expect(navigation.lanes).toHaveLength(94)
    expect(navigation.namedWaypoints).toHaveLength(46)
    expect(navigation.chargingWaypoints.map((vertex) => vertex.name)).toEqual(['charging_station'])
    expect(navigation.doors).toHaveLength(32)
  })

  it('uses a fixed inverted-Y transform aligned with the centered GLB', () => {
    const reception = navigation.vertices.find((vertex) => vertex.name === 'reception_back')
    const world = rmfToThree(reception)
    expect(rmfMapTransform.invertY).toBe(true)
    expect(world.x).toBeCloseTo(-0.780503, 5)
    expect(world.z).toBeCloseTo(4.670986, 5)
  })

  it('builds active routes dynamically and keeps every hop on an actual RMF lane', () => {
    const lanes = new Set(navigation.lanes.map((lane) => `${lane.from}:${lane.to}`))
    const ids = buildActiveRoutes(navigation, [{
      id: 'T001', robotId: 'R01', title: '藥品配送', origin: 'Pharmacy',
      destination: 'Nurse Reception', priority: 'high', startTime: '09:30:00', status: 'executing',
    }])[0].vertexIds
    ids.slice(1).forEach((id, index) => expect(lanes.has(`${ids[index]}:${id}`)).toBe(true))
  })

  it('uses the actual Graph 0 path and yellow visual treatment for Robot 02', () => {
    const route = buildActiveRoutes(navigation, [{
      id: 'T002', robotId: 'R02', title: '檢體運送', origin: 'Consultation Room 2',
      destination: 'Laboratory', priority: 'normal', startTime: '11:00:00', status: 'executing',
    }])[0]
    expect(route.vertexIds).toEqual(['v28', 'v25', 'v24', 'v0', 'v1', 'v16', 'v17', 'v18', 'v36'])
    expect(route.colors.main).toBe(0xd5ad4e)
    expect(robotVisualThemes.R02.main).toBe('#D5AD4E')
    expect(robotVisualThemes.R03.main).toBe('#4F9F91')
    expect(robotVisualThemes.R01.main).toBe('#CF7540')
    expect(semanticColors.success).toBe('#6F9B7B')
    expect(semanticColors.destination).toBe('#C96561')
  })

  it('draws the entire active route in saturated color and overlays completed segments', () => {
    const route = buildActiveRoutes(navigation, [{
      id: 'T001', robotId: 'R01', title: '藥品配送', origin: 'Pharmacy',
      destination: 'Nurse Reception', priority: 'high', startTime: '09:30:00', status: 'executing',
    }])[0]
    const parent = new THREE.Group()
    const layer = new RmfNavigationLayer({
      data: navigation,
      parent,
      routes: [route],
      camera: new THREE.PerspectiveCamera(),
      showRobotModels: false,
    })
    const entry = layer.routeEntries[0]
    expect(entry.activeRouteGroup.children).toHaveLength((route.vertexIds.length - 1) * 2 + 1)
    expect(entry.activeRouteGroup.children.every((mesh) => mesh.material.color.getHex() === 0xcf7540)).toBe(true)
    expect(entry.activeRouteGroup.children.every((mesh) => mesh.material.opacity === 0.82 && mesh.material.blending === THREE.NormalBlending && mesh.renderOrder === 2)).toBe(true)
    expect(entry.completedRouteGroup.children.length).toBeGreaterThan(0)
    expect(entry.completedRouteGroup.children.every((mesh) => mesh.material.color.getHex() === 0xb85f32 && mesh.renderOrder === 3)).toBe(true)
    const firstArrowPosition = entry.arrows[0].position.clone()
    layer.update(0.5)
    expect(entry.arrows[0].position.distanceTo(firstArrowPosition)).toBeGreaterThan(0.01)
    layer.dispose()
  })

  it('controls navigation, active routes, arrows, and robots independently', () => {
    const route = buildActiveRoutes(navigation, [{
      id: 'T001', robotId: 'R01', title: '藥品配送', origin: 'Pharmacy',
      destination: 'Nurse Reception', priority: 'high', startTime: '09:30:00', status: 'executing',
    }])[0]
    const layer = new RmfNavigationLayer({
      data: navigation,
      parent: new THREE.Group(),
      routes: [route],
      camera: new THREE.PerspectiveCamera(),
      showRobotModels: false,
    })

    layer.setBaseVisible(false)
    expect(layer.baseGroup.visible).toBe(false)
    expect(layer.activeGroup.visible).toBe(true)

    layer.setActiveVisible(false)
    expect(layer.activeGroup.visible).toBe(false)
    expect(layer.completedGroup.visible).toBe(false)
    expect(layer.baseGroup.visible).toBe(false)

    layer.setArrowsVisible(false)
    expect(layer.routeEntries[0].arrows.every((arrow) => !arrow.visible)).toBe(true)
    expect(layer.activeGroup.visible).toBe(false)

    layer.setRobotsVisible(false)
    expect(layer.robotGroup.visible).toBe(false)
    expect(layer.baseGroup.visible).toBe(false)

    layer.dispose()
  })

  it('keeps base, active, selected, and hit-target dimensions explicit', () => {
    expect(routeVisualConfig).toMatchObject({
      baseRouteRadius: 0.04,
      width: 0.32,
      activeRouteRadius: 0.16,
      selectedRouteRadius: 0.192,
      opacity: 0.82,
      arrowLength: 0.42,
      arrowWidth: 0.34,
      arrowSpacing: 1.15,
      arrowFlowSpeed: 0.9,
      baseHeight: 0.025,
      routeHeight: 0.055,
      completedHeight: 0.065,
      arrowHeight: 0.085,
    })
    expect(robotRouteColors.R01).toMatchObject({ main: 0xcf7540, completed: 0xb85f32 })
    expect(routeLayerY).toEqual({ R01: 0.031, R02: 0.034, R03: 0.037 })
    expect(REALTIME_ROBOT_SCALE_MULTIPLIER).toBe(1.4)
    expect(ROBOT_HIT_TARGET).toMatchObject({ radius: 0.45, height: 0.8 })
  })

  it('uses idle, approaching, and arrived destination states without changing to success green', () => {
    const container = document.createElement('div')
    const canvas = document.createElement('canvas')
    canvas.getBoundingClientRect = () => ({ width: 800, height: 600, left: 0, top: 0 })
    const parent = new THREE.Group()
    const camera = new THREE.PerspectiveCamera()
    const environmentGroup = new THREE.Group()
    const waypoint = navigation.namedWaypoints.find((entry) => entry.name === 'lab')
    const layer = new LocationMarkerLayer({
      data: { namedWaypoints: [waypoint] },
      details: { lab: { label: 'Laboratory', taskId: 'T002', robotId: 'R02', robot: 'Robot 02', isDestination: true, color: 0xffc400, theme: robotVisualThemes.R02 } },
      parent, container, camera, canvas, environmentGroup,
    })
    const entry = layer.entries[0]
    expect(entry.root.querySelector('.rmf-location__status')).toBeNull()
    expect(entry.root.style.getPropertyValue('--robot-color')).toBe('#D5AD4E')
    const farPosition = entry.nodeWorld.clone().add(new THREE.Vector3(2, 0, 0))
    layer.setDestinationState([{ id: 'T002', status: 'executing' }], new Map([['R02', farPosition]]), new Map([['R02', { progress: 0.2, isFinalSegment: false }]]))
    expect(entry.destinationState).toBe('idle')
    expect(entry.cube.material.opacity).toBe(0.14)
    layer.setDestinationState([{ id: 'T002', status: 'executing' }], new Map([['R02', farPosition]]), new Map([['R02', { progress: 0.8, isFinalSegment: false }]]))
    expect(entry.destinationState).toBe('approaching')
    expect(entry.cube.material.opacity).toBe(0.42)
    expect(entry.pin).toBeTruthy()
    layer.setDestinationState([{ id: 'T002', status: 'arrived' }], new Map([['R02', farPosition]]))
    expect(entry.destinationState).toBe('idle')
    const arrivedPosition = entry.nodeWorld.clone().add(new THREE.Vector3(0.1, 0, 0))
    layer.setDestinationState([{ id: 'T002', status: 'arrived' }], new Map([['R02', arrivedPosition]]))
    expect(entry.destinationState).toBe('arrived')
    expect(entry.cube.material.color.getHex()).toBe(0xffc400)
    expect(entry.cube.material.opacity).toBe(0.96)
    expect(entry.cube.material.emissiveIntensity).toBe(0.9)
    expect(entry.marker.scale.x).toBeCloseTo(0.74 / 0.66)
    expect(entry.pin.userData.materials[0].color.getHex()).toBe(0xc96561)
    expect(entry.pin.userData.materials[0].depthTest).toBe(false)
    expect(entry.pin.userData.baseScale).toBe(1.32)
    expect(entry.pin.position.y).toBeCloseTo(rmfToThree(waypoint).y + 0.55)
    layer.dispose()
  })

  it('uses neutral gray for the fixed charging station without changing Robot 03 routes', () => {
    const container = document.createElement('div')
    const canvas = document.createElement('canvas')
    const parent = new THREE.Group()
    const waypoint = navigation.namedWaypoints.find((entry) => entry.name === 'charging_station')
    const layer = new LocationMarkerLayer({
      data: { namedWaypoints: [waypoint] },
      details: { charging_station: { label: 'Charging Station A', statusKey: 'charging' } },
      parent,
      container,
      canvas,
      camera: new THREE.PerspectiveCamera(),
      environmentGroup: new THREE.Group(),
    })
    const entry = layer.entries[0]
    expect(entry.cube.material.color.getHex()).toBe(0x8f9692)
    expect(entry.outline.material.color.getHex()).toBe(0x8f9692)
    expect(entry.root.classList.contains('is-charging-station')).toBe(true)
    expect(entry.root.style.getPropertyValue('--location-color')).toBe('#8f9692')

    const chargingRoute = buildActiveRoutes(navigation, [{
      id: 'T006', robotId: 'R03', title: '前往充電', origin: 'Ward A', destination: 'Charging Station A',
      priority: 'normal', startTime: '16:00:00', status: 'executing', direction: 'outbound',
    }])[0]
    expect(chargingRoute.colors.main).toBe(0x4f9f91)
    layer.dispose()
  })

  it('reverses Graph 0 vertices and the active destination for a return leg', () => {
    const task = {
      id: 'T001', robotId: 'R01', title: '藥品配送', origin: 'Pharmacy',
      destination: 'Nurse Reception', direction: 'return', priority: 'high', status: 'executing',
    }
    const route = buildActiveRoutes(navigation, [task])[0]
    expect(route.vertexIds[0]).toBe(navigation.namedWaypoints.find((entry) => entry.name === 'reception_back').id)
    expect(route.vertexIds.at(-1)).toBe(navigation.namedWaypoints.find((entry) => entry.name === 'pharmacy').id)
    const details = buildLocationDetails([task])
    expect(details.pharmacy.isDestination).toBe(true)
    expect(details.reception_back.isDestination).toBe(false)
  })
})
