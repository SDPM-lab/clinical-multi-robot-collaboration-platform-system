import { afterEach, describe, expect, it } from 'vitest'
import {
  defaultRobotCameraPreset,
  readRobotCameraPreset,
  readRobotModelPreset,
  ROBOT_CAMERA_PRESET_KEY,
  ROBOT_MODEL_PRESET_KEY,
  storeRobotCameraPreset,
  storeRobotModelPreset,
  validRobotCameraPreset,
} from '@/config/robotViewportPreset.js'

afterEach(() => {
  localStorage.removeItem(ROBOT_CAMERA_PRESET_KEY)
  localStorage.removeItem(ROBOT_MODEL_PRESET_KEY)
})

describe('Robot Status view presets', () => {
  it('uses the shared camera preset with its reference aspect ratio', () => {
    expect(defaultRobotCameraPreset()).toEqual({
      position: { x: 3.093, y: 1.018, z: 0.588 },
      target: { x: 0.02, y: 0.648, z: 0.019 },
      fov: 35,
      aspect: 1.0703911870503597,
    })
    expect(validRobotCameraPreset(defaultRobotCameraPreset())).toBe(true)
  })

  it('persists camera and model settings for the normal page', () => {
    const camera = { position: { x: 1, y: 2, z: 3 }, target: { x: 0, y: 0, z: 0 }, fov: 35, aspect: 1.5 }
    const model = { position: { x: 0.2, y: 0, z: 0 }, rotationY: Math.PI / 4, scale: 1.1 }

    storeRobotCameraPreset(camera)
    storeRobotModelPreset(model)

    expect(readRobotCameraPreset()).toEqual(camera)
    expect(readRobotModelPreset()).toEqual(model)
  })

  it('ignores malformed camera data and camera positions at the target', () => {
    expect(validRobotCameraPreset({ position: { x: 0, y: 0, z: 0 }, target: { x: 0, y: 0, z: 0 }, fov: 35 })).toBe(false)
    expect(validRobotCameraPreset({ position: { x: 1, y: 0, z: 0 }, target: { x: 0, y: 0, z: 0 }, fov: 35, aspect: 0 })).toBe(false)
    localStorage.setItem(ROBOT_CAMERA_PRESET_KEY, '{broken')
    expect(readRobotCameraPreset()).toBeNull()
  })
})
