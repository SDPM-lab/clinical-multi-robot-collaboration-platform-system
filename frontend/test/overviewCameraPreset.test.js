import { beforeEach, describe, expect, it } from 'vitest'

import {
  DEFAULT_OVERVIEW_CAMERA_PRESET,
  isOverviewCameraPreset,
  OVERVIEW_CAMERA_PRESET_STORAGE_KEY,
  readStoredOverviewCameraPreset,
  storeOverviewCameraPreset,
} from '@/three/overviewCameraPreset.js'

const preset = {
  positionOffset: [1, 2, 3],
  targetOffset: [0, 0, 0],
  zoom: 1.5,
  position: [1, 2, 3],
  target: [0, 0, 0],
  quaternion: [0, 0, 0, 1],
}

describe('overview camera preset storage', () => {
  beforeEach(() => localStorage.clear())

  it('accepts a finite, positive relative camera preset', () => {
    expect(isOverviewCameraPreset(DEFAULT_OVERVIEW_CAMERA_PRESET)).toBe(true)
    expect(isOverviewCameraPreset(preset)).toBe(true)
    expect(isOverviewCameraPreset({ ...preset, zoom: 0 })).toBe(false)
    expect(isOverviewCameraPreset({ ...preset, positionOffset: [1, 2] })).toBe(false)
  })

  it('stores and restores the debug preset', () => {
    storeOverviewCameraPreset(preset)

    expect(localStorage.getItem(OVERVIEW_CAMERA_PRESET_STORAGE_KEY)).toBe(JSON.stringify(preset))
    expect(readStoredOverviewCameraPreset()).toEqual(preset)
  })

  it('ignores malformed stored values', () => {
    localStorage.setItem(OVERVIEW_CAMERA_PRESET_STORAGE_KEY, '{not json')

    expect(readStoredOverviewCameraPreset()).toBeNull()
  })
})
