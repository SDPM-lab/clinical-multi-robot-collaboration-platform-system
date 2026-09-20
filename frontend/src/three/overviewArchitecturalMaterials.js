import * as THREE from 'three'

export const overviewGlassNames = new Set(['M_Glass', 'M_DoorGlass'])
export const overviewGlassParameters = Object.freeze({ color:'#AEB9B5', transparent:true, opacity:.26, transmission:.68, roughness:.16, metalness:0, ior:1.45, thickness:.06, depthWrite:false, side:THREE.DoubleSide })
export const overviewSaturationScale = 1.08
const warmMaterials = { M_WoodLouvers: '#9B6A48', M_Soffit: '#674B3A' }

export function enhanceOverviewModelSaturation(root, scale = overviewSaturationScale) {
  const adjusted = new Set()
  const hsl = { h: 0, s: 0, l: 0 }
  root.traverse(object => {
    if (!object.isMesh || !object.material) return
    const materials = Array.isArray(object.material) ? object.material : [object.material]
    materials.forEach(material => {
      if (!material?.color || adjusted.has(material)) return
      adjusted.add(material)
      material.color.getHSL(hsl)
      if (hsl.s <= 0.01) return
      material.color.setHSL(hsl.h, Math.min(1, hsl.s * scale), hsl.l)
      material.needsUpdate = true
    })
  })
}

// Exact GLB material names only. Textures and exported emissive remain intact.
export function applyOverviewArchitecturalMaterials(root, registerMaterial) {
  root.traverse(object => {
    if (!object.isMesh) return
    const array = Array.isArray(object.material)
    const materials = (array ? object.material : [object.material]).map(material => {
      if (overviewGlassNames.has(material.name)) {
        let glass = material
        if (!material.isMeshPhysicalMaterial) {
          glass = new THREE.MeshPhysicalMaterial()
          THREE.MeshStandardMaterial.prototype.copy.call(glass, material)
          registerMaterial(glass)
        }
        glass.setValues(overviewGlassParameters)
        glass.needsUpdate = true
        return glass
      }
      if (warmMaterials[material.name]) {
        // Blend from the exported value rather than replacing architecture wholesale.
        material.color.lerp(new THREE.Color(warmMaterials[material.name]), material.name === 'M_WoodLouvers' ? .38 : .25)
        material.needsUpdate = true
      }
      return material
    })
    object.material = array ? materials : materials[0]
  })
}
