const publicAssetUrl = (path, version) => `${import.meta.env?.BASE_URL || '/'}${path}${version ? `?v=${version}` : ''}`

export const SCENE_ASSETS = Object.freeze({
  environment: publicAssetUrl('models/hospital_L1_environment.glb', 'a0b280479946'),
  robot: publicAssetUrl('models/robot.glb', '4138e4f67c9e'),
  robots: Object.freeze([publicAssetUrl('models/robot.glb', '4138e4f67c9e')]),
  characters: Object.freeze([]),
  overlays: Object.freeze([]),
})

export const NAVIGATION_ASSETS = Object.freeze({
  graph0: publicAssetUrl('generated/rmf-navigation.json', '209581c07be5'),
  graph1: publicAssetUrl('generated/rmf-navigation-graph-1.json', 'a76216b3a527'),
})

// These are exact root object names found in the original combined hospital GLB.
// Do not replace them with broad includes("robot") / includes("nurse") checks:
// OpenRobotics is also the namespace used by static hospital furniture, and
// NurseTable / NurseMonitor are equipment rather than characters.
export const EMBEDDED_DYNAMIC_ROOTS = Object.freeze({
  robots: Object.freeze([
    'hospital_robot_1',
    'hospital_robot_2',
    'hospital_robot_3',
    'hospital_robot_4',
  ]),
  characters: Object.freeze([
    'OpenRobotics/FemaleVisitorSit',
    'OpenRobotics/FemaleVisitorSit_2',
    'OpenRobotics/FemaleVisitorSit_3',
    'OpenRobotics/MaleVisitorSit',
    'OpenRobotics/Standing person',
    'OpenRobotics/Nurse',
  ]),
})

const robotRootNames = new Set(EMBEDDED_DYNAMIC_ROOTS.robots)
const characterRootNames = new Set(EMBEDDED_DYNAMIC_ROOTS.characters)

export function getEmbeddedAssetLayer(objectName) {
  if (robotRootNames.has(objectName)) return 'robots'
  if (characterRootNames.has(objectName)) return 'characters'
  return null
}
