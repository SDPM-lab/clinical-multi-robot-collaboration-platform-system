import { describe, expect, it, afterEach } from 'vitest'
import { readFileSync } from 'node:fs'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { Box3 } from 'three'
import { thermalState, batteryColor, batteryLiquidColors, robotThermalZones } from '@/config/robotHmi.js'
import { chargingCommandAdapter } from '@/services/chargingCommandAdapter.js'
import { fleetStore } from '@/stores/demoFleetStore.js'
afterEach(() => fleetStore.robots.value.forEach(r => { r.chargingCommand = null }))
describe('HMI telemetry and asset contract', () => {
  it('uses exact threshold boundaries', () => {
    expect([null, 54, 54.9, 69, 70].map(thermalState)).toEqual(['unknown', 'normal', 'warning', 'warning', 'critical'])
    expect(batteryColor(19)).toBe('#C96561')
    expect(batteryColor(20)).toBe('#D5AD4E')
    expect(batteryColor(40)).toBe('#D5AD4E')
    expect(batteryColor(41)).toBe('#C96F3B')
    expect(batteryColor(10, true)).toBe('#4F9F91')
    expect(batteryLiquidColors(82)).toEqual(['#D29A72', '#A96547'])
    expect(batteryLiquidColors(40)).toEqual(['#D7B66B', '#A9833F'])
    expect(batteryLiquidColors(20)).toEqual(['#C97872', '#98524F'])
    expect(batteryLiquidColors(20, true)).toEqual(['#8BBAB0', '#4F8178'])
  })
  it('maps exact runtime GLB names only to the bottom chassis geometry', async () => {
    const bytes = readFileSync('public/models/robot.glb')
    const gltf = await new GLTFLoader().parseAsync(new Uint8Array(bytes).buffer, '')
    gltf.scene.updateMatrixWorld(true)
    const full = new Box3().setFromObject(gltf.scene)
    for (const name of robotThermalZones.chassis) {
      const mesh = gltf.scene.getObjectByName(name)
      expect(mesh?.isMesh).toBe(true)
      const bounds = new Box3().setFromObject(mesh)
      expect(bounds.max.y).toBeLessThan(full.max.y * .08)
    }
    gltf.scene.traverse(m => { if (m.isMesh) { m.geometry.dispose(); m.material.dispose() } })
  })
  it('rejects charging while the control service is unavailable without mutating state', async () => {
    const before = JSON.stringify(fleetStore.state)
    expect(chargingCommandAdapter.available).toBe(false)
    await expect(chargingCommandAdapter.dispatch('R01')).rejects.toThrow('控制服務未連線')
    expect(JSON.stringify(fleetStore.state)).toBe(before)
  })
})
