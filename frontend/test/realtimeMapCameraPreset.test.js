import { beforeEach, describe, expect, it } from 'vitest'

import {
  DEFAULT_REALTIME_MAP_CAMERA_PRESET,
  isRealtimeMapCameraPreset,
  readStoredRealtimeMapCameraPreset,
  REALTIME_MAP_CAMERA_PRESET_STORAGE_KEY,
  storeRealtimeMapCameraPreset,
} from '@/three/realtimeMapCameraPreset.js'

const preset = {
  positionOffset: [4, 5, 6],
  targetOffset: [1, 2, 3],
  zoom: 1,
}

describe('realtime map camera preset storage', () => {
  beforeEach(() => localStorage.clear())

  it('validates relative camera data', () => {
    expect(isRealtimeMapCameraPreset(DEFAULT_REALTIME_MAP_CAMERA_PRESET)).toBe(true)
    expect(isRealtimeMapCameraPreset(preset)).toBe(true)
    expect(isRealtimeMapCameraPreset({ ...preset, zoom: -1 })).toBe(false)
  })

  it('stores and restores the calibration preset', () => {
    storeRealtimeMapCameraPreset(preset)

    expect(localStorage.getItem(REALTIME_MAP_CAMERA_PRESET_STORAGE_KEY)).toBe(JSON.stringify(preset))
    expect(readStoredRealtimeMapCameraPreset()).toEqual(preset)
  })
})
