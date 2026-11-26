import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js'
import { COMPRESSED_MODELS } from '@/config/compressedModels.js'

// Runtime models in public/models/draco/ are Draco-compressed (about 8x smaller than the
// source GLBs), so every loader needs the decoder. One DRACOLoader is shared so its
// worker pool and WASM module are created once for the whole app.
let dracoLoader = null

function sharedDracoLoader() {
  if (!dracoLoader) {
    dracoLoader = new DRACOLoader()
    dracoLoader.setDecoderPath(`${import.meta.env?.BASE_URL || '/'}draco/`)
    dracoLoader.setDecoderConfig({ type: 'wasm' })
  }
  return dracoLoader
}

export function createGltfLoader() {
  return new GLTFLoader().setDRACOLoader(sharedDracoLoader())
}

// Maps a source model URL (e.g. /models/robot.glb?v=abc) to its compressed runtime copy.
// URLs without a compressed copy (uploads, other files) are returned unchanged.
export function runtimeModelUrl(url) {
  const match = /^(.*\/)models\/([^/?#]+\.glb)(?:[?#].*)?$/.exec(url)
  const entry = match && COMPRESSED_MODELS[match[2]]
  return entry ? `${match[1]}models/draco/${match[2]}?v=${entry.version}` : url
}
