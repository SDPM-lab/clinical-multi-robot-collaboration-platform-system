const freezeRule = (rule) => Object.freeze({
  materialNames: Object.freeze(rule.materialNames || []),
  materialPrefixes: Object.freeze(rule.materialPrefixes || []),
  objectPrefixes: Object.freeze(rule.objectPrefixes || []),
})

export const overviewMaterialRules = Object.freeze({
  woodAccent: freezeRule({
    materialNames: [
      'MAT_RoomDoor_LightWood',
      // The exported consult 2/3 door leaves use this exact material name.
      'MAT_RoomDoor_Frame.001',
    ],
  }),
  woodAccentDark: freezeRule({
    materialNames: ['MAT_RoomDoor_Frame'],
  }),
  wall: freezeRule({
    materialNames: ['MAT_Wall_WarmWhite'],
  }),
  floor: freezeRule({
    materialNames: ['MAT_Hospital_Floor'],
  }),
  glass: freezeRule({
    materialNames: ['MAT_MainEntrance_Glass'],
  }),
  structure: freezeRule({
    materialNames: ['MAT_Reception_WarmIvory'],
  }),
  furniture: freezeRule({
    materialPrefixes: [
      'MAT_OfficeChair_',
      'MAT_OfficeChairBlue_',
      'MAT_Chair_',
      'MAT_PotatoChair_',
      'MAT_Bed_',
      'MAT_BedTable_',
      'MAT_Bedside_',
      'MAT_AdjTable_',
      'MAT_Bookshelf_',
      'MAT_Wardrobe_',
      'MAT_MeetingTable_',
    ],
    objectPrefixes: [
      'OpenRobotics/MiniSofa',
      'OpenRobotics/Chair',
      'OpenRobotics/TrolleyBed',
      'OpenRobotics/Table',
      'OpenRobotics/MetalCabinet',
      'OpenRobotics/SquareShelf',
      'OpenRobotics/StorageRack',
      'OpenRobotics/Fridge',
    ],
  }),
  equipment: freezeRule({
    materialNames: ['DoorHandle3.003'],
    materialPrefixes: [
      'MAT_BPM_',
      'MAT_Computer_',
      'MAT_CGM_',
      'MAT_IVStand_',
      'MAT_BathroomSink_',
      'MAT_KitchenSink_',
      'MAT_TrashBin_',
      'MAT_LitterBin_',
      'MAT_Drawer_',
      'MAT_Toilet_',
    ],
    objectPrefixes: [
      'OpenRobotics/XRayMachine',
      'OpenRobotics/BPCart',
      'OpenRobotics/ScrubsTrolley',
      'OpenRobotics/CleaningSection',
    ],
  }),
})

const orderedCategories = Object.freeze([
  'woodAccent',
  'woodAccentDark',
  'wall',
  'floor',
  'glass',
  'structure',
  'furniture',
  'equipment',
])

const objectHierarchyNames = (object) => {
  const names = []
  let current = object

  while (current) {
    if (current.name) names.push(String(current.name))
    current = current.parent
  }

  return names
}

const matchesRule = (rule, object, materialName) => (
  rule.materialNames.includes(materialName)
  || rule.materialPrefixes.some((prefix) => materialName.startsWith(prefix))
  || objectHierarchyNames(object).some((name) => (
    rule.objectPrefixes.some((prefix) => name.startsWith(prefix))
  ))
)

export function classifyOverviewMaterial(object, material) {
  const materialName = String(material?.name || '')

  for (const category of orderedCategories) {
    if (matchesRule(overviewMaterialRules[category], object, materialName)) return category
  }

  // Unknown fixed geometry stays neutral instead of inheriting original color.
  return 'structure'
}

export function collectOverviewMeshMaterialRows(root) {
  const rows = []

  root?.traverse((object) => {
    if (!object.isMesh || !object.material) return
    const materials = Array.isArray(object.material) ? object.material : [object.material]

    materials.forEach((material) => {
      rows.push({
        object: object.name || '(unnamed mesh)',
        material: material?.name || '(unnamed material)',
        category: classifyOverviewMaterial(object, material),
      })
    })
  })

  return rows
}
