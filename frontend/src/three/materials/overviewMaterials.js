import * as THREE from 'three'
import { classifyOverviewMaterial } from '@/three/overviewMaterialRules.js'

const originalMaterials = new WeakMap()

function overviewMaterial(object, original, palette) {
  const category = classifyOverviewMaterial(object, original)
  const isGlass = category === 'glass'
  const isWood = category === 'woodAccent' || category === 'woodAccentDark'
  const color = palette[category] ?? palette.structure
  const isWall = category === 'wall'
  const material = new THREE.MeshStandardMaterial({
    color,
    roughness: isGlass ? 0.18 : isWood ? (category === 'woodAccentDark' ? 0.84 : 0.82) : isWall ? 0.62 : 0.72,
    metalness: category === 'equipment' ? 0.14 : isWall ? 0.02 : 0.0,
    transparent: Boolean(original?.transparent) || isGlass,
    opacity: isGlass ? Math.min(original?.opacity ?? 0.35, 0.42) : 1,
    depthWrite: !isGlass,
  })

  if (isGlass) material.side = THREE.DoubleSide
  material.name = `Overview_${category}`
  material.userData.overviewCategory = category
  return material
}

export function applyOverviewMaterials(root, palette) {
  const classifications = new Map()

  root.traverse((object) => {
    if (!object.isMesh || !object.material) return

    const originals = Array.isArray(object.material)
      ? object.material.slice()
      : [object.material]
    originalMaterials.set(object, originals)
    object.material = originals.map((original) => {
      const category = classifyOverviewMaterial(object, original)
      classifications.set(category, (classifications.get(category) || 0) + 1)
      return overviewMaterial(object, original, palette)
    })
    if (object.material.length === 1) object.material = object.material[0]
  })

  return Object.fromEntries(classifications)
}

export function updateOverviewMaterialTheme(root, palette) {
  root?.traverse((object) => {
    if (!object.isMesh || !object.material) return

    const materials = Array.isArray(object.material) ? object.material : [object.material]
    materials.forEach((material) => {
      const category = material?.userData?.overviewCategory
      if (!category) return
      material.color.setHex(palette[category] ?? palette.structure)
      material.needsUpdate = true
    })
  })
}

export function restoreOriginalMaterials(root) {
  root?.traverse((object) => {
    const originals = originalMaterials.get(object)
    if (!originals) return
    object.material = originals.length === 1 ? originals[0] : originals
    originalMaterials.delete(object)
  })
}

export function disposeOverviewMaterials(root) {
  root?.traverse((object) => {
    const originals = originalMaterials.get(object)
    if (!originals) return
    const current = Array.isArray(object.material) ? object.material : [object.material]
    current.forEach((material) => material?.dispose())
    object.material = originals.length === 1 ? originals[0] : originals
    originalMaterials.delete(object)
  })
}
