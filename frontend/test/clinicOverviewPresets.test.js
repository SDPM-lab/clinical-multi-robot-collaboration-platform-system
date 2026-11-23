import { beforeEach, describe, expect, it } from 'vitest'
import {
  OVERVIEW_CAMERA_PRESET_STORAGE_KEY,
  OVERVIEW_MODEL_PRESET_STORAGE_KEY,
  clearOverviewCameraPreset,
  clearOverviewModelPreset,
  cloneDefaultOverviewCameraPreset,
  cloneDefaultOverviewModelPreset,
  readOverviewCameraPreset,
  readOverviewModelPreset,
  storeOverviewCameraPreset,
  storeOverviewModelPreset,
} from '@/three/clinicOverviewPresets.js'

const cameraPreset = {
  position: { x: 12, y: 8, z: 16 },
  target: { x: 1, y: 2, z: 3 },
}
const modelPreset = {
  position: { x: 2, y: -1, z: 4 },
  rotation: { x: 0, y: 0.75, z: 0 },
  scale: 1.2,
}

describe('clinic overview presets', () => {
  beforeEach(() => localStorage.clear())

  it('stores camera and model values under separate stable keys', () => {
    storeOverviewCameraPreset(cameraPreset)
    storeOverviewModelPreset(modelPreset)

    expect(OVERVIEW_CAMERA_PRESET_STORAGE_KEY).toBe('overview-camera-preset-v9')
    expect(OVERVIEW_MODEL_PRESET_STORAGE_KEY).toBe('overview-model-preset-v4')
    expect(readOverviewCameraPreset()).toEqual(cameraPreset)
    expect(readOverviewModelPreset()).toEqual(modelPreset)
  })

  it('rejects malformed values and clears each preset independently', () => {
    localStorage.setItem(OVERVIEW_CAMERA_PRESET_STORAGE_KEY, '{bad json')
    localStorage.setItem(OVERVIEW_MODEL_PRESET_STORAGE_KEY, JSON.stringify({ scale: 1 }))
    expect(readOverviewCameraPreset()).toBeNull()
    expect(readOverviewModelPreset()).toBeNull()

    storeOverviewCameraPreset(cameraPreset)
    storeOverviewModelPreset(modelPreset)
    clearOverviewCameraPreset()
    expect(readOverviewCameraPreset()).toBeNull()
    expect(readOverviewModelPreset()).toEqual(modelPreset)
    clearOverviewModelPreset()
    expect(readOverviewModelPreset()).toBeNull()
  })

  it('uses the approved model and camera defaults', () => {
    expect(cloneDefaultOverviewModelPreset()).toEqual({
      position: { x: -2.6711178700891924, y: 3.9159005573132415, z: -0.0891364507224327 },
      rotation: { x: 0, y: 0.40120019531249995, z: 0 },
      scale: 0.8951884436412747,
    })
    expect(cloneDefaultOverviewCameraPreset()).toEqual({
      position: { x: 28.068, y: 15.9581, z: 52.631 },
      target: { x: -0.6117, y: 6.0941, z: 2.5053 },
    })
    localStorage.setItem('overviewModelPreset', JSON.stringify(modelPreset))
    localStorage.setItem('overviewCameraPreset', JSON.stringify(cameraPreset))
    localStorage.setItem('overviewModelPreset:v2', JSON.stringify(modelPreset))
    localStorage.setItem('overviewCameraPreset:v2', JSON.stringify(cameraPreset))
    expect(readOverviewModelPreset()).toBeNull()
    expect(readOverviewCameraPreset()).toBeNull()
  })
})
