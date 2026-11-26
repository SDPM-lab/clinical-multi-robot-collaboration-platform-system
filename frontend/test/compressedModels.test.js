import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { COMPRESSED_MODELS } from '@/config/compressedModels.js'
import { runtimeModelUrl } from '@/three/loaders/createGltfLoader.js'

const hash = file => createHash('sha256').update(readFileSync(file)).digest('hex').slice(0, 12)

describe('compressed runtime models', () => {
  it.each(Object.entries(COMPRESSED_MODELS))('%s matches its source GLB (run npm run models:compress if this fails)', (name, entry) => {
    expect(hash(`public/models/${name}`)).toBe(entry.source)
    expect(hash(`public/models/draco/${name}`)).toBe(entry.version)
  })

  it('maps source model URLs to their compressed copies', () => {
    expect(runtimeModelUrl('/models/robot.glb?v=4138e4f67c9e')).toBe(`/models/draco/robot.glb?v=${COMPRESSED_MODELS['robot.glb'].version}`)
    expect(runtimeModelUrl('/models/baymax_nurse.glb')).toBe(`/models/draco/baymax_nurse.glb?v=${COMPRESSED_MODELS['baymax_nurse.glb'].version}`)
    expect(runtimeModelUrl('/models/unknown.glb')).toBe('/models/unknown.glb')
  })
})
