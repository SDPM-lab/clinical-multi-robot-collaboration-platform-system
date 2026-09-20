const snapshots = new Map()
let activeGraphSignature = null

export const graphActorRuntimeStore = {
  prepare(graphSignature) {
    if (activeGraphSignature === graphSignature) return
    activeGraphSignature = graphSignature
    snapshots.clear()
  },

  get(actorId) {
    const snapshot = snapshots.get(actorId)
    return snapshot ? structuredClone(snapshot) : null
  },

  save(actorId, snapshot) {
    snapshots.set(actorId, structuredClone(snapshot))
  },

  clear() {
    activeGraphSignature = null
    snapshots.clear()
  },
}
