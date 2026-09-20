// Snapshots stay outside userData, which Three.js copies through JSON.
export function captureOverviewOriginalState(root, registerMaterial) {
  const states = new Map()
  root.traverse(object => {
    const state = { visible: object.visible, position: object.position.clone(), quaternion: object.quaternion.clone(), scale: object.scale.clone() }
    if (object.isMesh) {
      const array = Array.isArray(object.material)
      const originals = (array ? object.material : [object.material]).map(material => {
        registerMaterial(material)
        const snapshot = material.clone()
        registerMaterial(snapshot)
        return snapshot
      })
      const working = originals.map(material => { const clone = material.clone(); registerMaterial(clone); return clone })
      object.material = array ? working : working[0]
      state.materials = originals
    }
    states.set(object, state)
  })
  return states
}
export function restoreOverviewOriginalState(states) {
  for (const [object, state] of states) {
    object.visible = state.visible
    object.position.copy(state.position)
    object.quaternion.copy(state.quaternion)
    object.scale.copy(state.scale)
    if (state.materials) {
      const materials = Array.isArray(object.material) ? object.material : [object.material]
      materials.forEach((material, index) => { material.copy(state.materials[index]); material.needsUpdate = true })
    }
  }
}
