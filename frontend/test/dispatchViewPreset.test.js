import { afterEach, describe, expect, it } from 'vitest'
import {
  DISPATCH_CAMERA_PRESET_KEY, DISPATCH_MODEL_PRESET_KEY,
  defaultDispatchModelPreset, readDispatchCameraPreset, readDispatchModelPreset,
  storeDispatchCameraPreset, storeDispatchModelPreset, validDispatchCameraPreset,
} from '@/config/dispatchViewPreset.js'

afterEach(() => { localStorage.removeItem(DISPATCH_CAMERA_PRESET_KEY); localStorage.removeItem(DISPATCH_MODEL_PRESET_KEY) })

describe('Task Dispatch display presets', () => {
  it('persists valid camera and model settings and rejects malformed input', () => {
    const camera = { position: { x: 1, y: 48, z: 25 }, target: { x: 0, y: 0, z: 0 }, zoom: 1.25 }
    expect(validDispatchCameraPreset({ ...camera, zoom: 0 })).toBe(false)
    storeDispatchCameraPreset(camera)
    storeDispatchModelPreset(defaultDispatchModelPreset())
    expect(readDispatchCameraPreset()).toEqual(camera)
    expect(readDispatchModelPreset()).toEqual(defaultDispatchModelPreset())
    localStorage.setItem(DISPATCH_CAMERA_PRESET_KEY, '{bad json')
    expect(readDispatchCameraPreset()).toBeNull()
  })
})
