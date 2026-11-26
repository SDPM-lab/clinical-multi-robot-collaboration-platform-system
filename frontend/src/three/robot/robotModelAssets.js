import * as THREE from 'three'
import { createGltfLoader, runtimeModelUrl } from '@/three/loaders/createGltfLoader.js'

export const DEFAULT_ROBOT_ASSET = 'AGIBOT_A2D'
const defaultUrl = runtimeModelUrl(`${import.meta.env.BASE_URL}models/AGIBOT_A2D.glb`)
const assets = new Map()
let nextAssetId = 0

export function loadRobotAsset(key = DEFAULT_ROBOT_ASSET) {
  if (key !== DEFAULT_ROBOT_ASSET && !assets.has(key)) return Promise.reject(new Error('Uploaded robot model is unavailable'))
  if (!assets.has(key)) {
    const promise = createGltfLoader().loadAsync(defaultUrl).catch(error => {
      assets.delete(key)
      throw error
    })
    assets.set(key, promise)
  }
  return assets.get(key)
}

export async function registerRobotAsset(file) {
  if (!file || !/\.glb$/i.test(file.name)) throw new Error('Choose a .glb file')
  const buffer = await file.arrayBuffer()
  if (buffer.byteLength < 12 || new DataView(buffer).getUint32(0, true) !== 0x46546c67) throw new Error('Invalid GLB file')
  const asset = await createGltfLoader().parseAsync(buffer, '')
  let meshCount = 0
  asset.scene.traverse(object => { if (object.isMesh) meshCount++ })
  if (!meshCount || new THREE.Box3().setFromObject(asset.scene).isEmpty()) throw new Error('GLB has no visible mesh')
  const key = `uploaded-${++nextAssetId}`
  assets.set(key, Promise.resolve(asset))
  return key
}

export function unregisterRobotAsset(key) {
  if (key !== DEFAULT_ROBOT_ASSET) assets.delete(key)
}
