export const overviewFloorKeys = Object.freeze(['1', '2', '3'])

export const modelLoadPercentage = ({ loaded = 0, total = 0 } = {}) => (
  total > 0 ? Math.min(99, Math.max(0, Math.round((loaded / total) * 100))) : 0
)

export const normalizeOverviewNodeName = (name) => String(name || '')
  .trim()
  .toLowerCase()
  .replace(/\.\d{3}$/u, '')
  .replace(/[\s_-]+/gu, '')

const commonScenePattern = /(?:tree|parking|streetlamp|bollard|walkway|sitebase|displaybase|landscape|planter|shrub|dense|rock|(?:centerleft|centerright|leftfront|leftrear|rightrear)bed)/i
const sharedBuildingPattern = /(?:exteriorwall|emptyinteriorbackdrop|greenfacadepanel|signaturewhitecurve)/i
const ceilingLightPattern = /(?:ceilinglight|ceilingstrip|downlight|(?:^|web)f[123]light|lightfixture|emissiveplane|glowmesh|ledstrip|lamp)/i

export const floorIdFromOverviewName = (name) => {
  const normalized = normalizeOverviewNodeName(name)
  if (normalized.includes('firstfloor')) return '1'
  if (normalized.includes('secondfloor')) return '2'
  if (normalized.includes('thirdfloor')) return '3'
  if (/^hospital(?:cross|text)/u.test(normalized)) return '1'
  const namedFloor = normalized.match(/(?:floor|level0?|webfloor)([123])/u)?.[1]
  if (namedFloor) return namedFloor
  const collectionFloor = normalized.match(/^f([123])(?:structure|ceilinglights)/u)?.[1]
  if (collectionFloor) return collectionFloor
  const compactFloor = normalized.match(/(?:^|rightglass)f([123])(?:left|right|main|light|bottom|top|glass|mullion)/u)?.[1]
  if (compactFloor) return compactFloor
  if (/^(?:balcony|webbalcony)/u.test(normalized)) return '3'
  if (/^(?:roof|topcanopy)|upperbalcony/u.test(normalized)) return '3'
  return null
}

export const isOverviewCommonNode = (name) => {
  const normalized = normalizeOverviewNodeName(name)
  return commonScenePattern.test(normalized) || sharedBuildingPattern.test(normalized)
}

export const isOverviewSharedBuildingNode = (name) => sharedBuildingPattern.test(normalizeOverviewNodeName(name))

export const isOverviewCeilingLightNode = (objectOrName) => {
  const object = typeof objectOrName === 'string' ? null : objectOrName
  const name = normalizeOverviewNodeName(object?.name || objectOrName)
  if (/^(?:streetlamp|frontbollard|sidebollard|webtreeuplight)/u.test(name)) return false
  return ceilingLightPattern.test(name)
}

export const isOverviewFloorIsolationExcludedNode = isOverviewCeilingLightNode

export const isOverviewFloorCameraNode = (name) => {
  const normalized = normalizeOverviewNodeName(name)
  return !ceilingLightPattern.test(normalized)
}

export const classifyOverviewFloorObject = (object, bounds) => {
  const explicit = floorIdFromOverviewName(object?.name)
  if (explicit) return explicit
  if (isOverviewCommonNode(object?.name)) return null
  if (!bounds || bounds.isEmpty?.()) return null

  // The re-exported GLB is flat. Only unlabelled building pieces use the three
  // authored slab elevations as a fallback; semantic environment nodes above
  // were already excluded so tall trees and site lights remain common.
  if (bounds.max.y <= 3.35) return '1'
  if (bounds.min.y >= 6.2) return '3'
  if (bounds.min.y >= 3.0 && bounds.max.y <= 6.55) return '2'
  return null
}

export const createOverviewFloorGroups = () => ({ 1: [], 2: [], 3: [] })

export const buildOverviewFloorMapping = (root, Box3Class) => {
  const groups = createOverviewFloorGroups()
  const floorStructureGroups = createOverviewFloorGroups()
  const ceilingLightMeshes = []
  const common = []
  const sharedBuilding = []
  root.updateMatrixWorld(true)
  root.traverse((object) => {
    if (!object.isMesh) return
    const bounds = new Box3Class().setFromObject(object)
    let ancestor = object.parent
    let collectionFloor = null
    while (ancestor) {
      const match = normalizeOverviewNodeName(ancestor.name).match(/^f([123])(?:structure|ceilinglights)$/u)
      if (match) { collectionFloor = match[1]; break }
      ancestor = ancestor.parent
    }
    const floorId = collectionFloor || classifyOverviewFloorObject(object, bounds)
    const isCeilingLight = isOverviewCeilingLightNode(object)
    if (isCeilingLight) ceilingLightMeshes.push(object)
    if (floorId) {
      groups[floorId].push(object)
      if (!isCeilingLight) floorStructureGroups[floorId].push(object)
    }
    else {
      common.push(object)
      if (isOverviewSharedBuildingNode(object.name)) sharedBuilding.push(object)
    }
  })
  return { groups, floorStructureGroups, ceilingLightMeshes, common, sharedBuilding }
}
