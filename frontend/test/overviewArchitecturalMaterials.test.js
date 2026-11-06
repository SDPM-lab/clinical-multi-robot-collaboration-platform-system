import { expect, it } from 'vitest'
import * as THREE from 'three'
import { applyOverviewArchitecturalMaterials, enhanceOverviewModelSaturation, overviewGlassParameters, overviewSaturationScale } from '@/three/overviewArchitecturalMaterials.js'
import { captureOverviewOriginalState, restoreOverviewOriginalState } from '@/three/overviewOriginalState.js'
it('targets exported material names, preserves maps/emissive and restores the tuned baseline without cumulative changes',()=>{
 const root=new THREE.Group(), resources=new Set(), register=m=>resources.add(m)
 for(const name of ['M_Glass','M_DoorGlass','M_White','M_WoodLouvers','M_Soffit','OtherGlass']) {
  const material=new THREE.MeshStandardMaterial({color:'#789090',emissive:'#332211',emissiveIntensity:.4,map:new THREE.Texture()});material.name=name
  root.add(new THREE.Mesh(new THREE.BoxGeometry(),material))
 }
 const originals=captureOverviewOriginalState(root,register)
 applyOverviewArchitecturalMaterials(root,register)
 const baseline=captureOverviewOriginalState(root,register)
 for(const mesh of root.children) {
  const original=originals.get(mesh).materials[0]
  expect(mesh.material.map).toBe(original.map)
  expect(mesh.material.emissive.equals(original.emissive)).toBe(true)
  if(['M_Glass','M_DoorGlass'].includes(mesh.material.name)) {
   expect(mesh.material.isMeshPhysicalMaterial).toBe(true)
   for(const key of ['opacity','transmission','roughness','metalness','ior','thickness','side','depthWrite']) expect(mesh.material[key]).toBe(overviewGlassParameters[key])
  }
  if(['M_White','OtherGlass'].includes(mesh.material.name)) expect(mesh.material.color.equals(original.color)).toBe(true)
 }
 for(let i=0;i<5;i++) {
  root.children[0].material.opacity=.1
  restoreOverviewOriginalState(baseline)
  expect(root.children[0].material.opacity).toBe(.26)
  expect(root.children[0].material.transmission).toBe(.68)
 }
 resources.forEach(m=>m.dispose());root.children.forEach(m=>{m.geometry.dispose();m.material.map.dispose()})
})

it('slightly deepens overview model colors without changing lightness or neutral materials',()=>{
 const root=new THREE.Group()
 const green=new THREE.MeshStandardMaterial({color:'#4f9d61'})
 const neutral=new THREE.MeshStandardMaterial({color:'#a0a0a0'})
 root.add(new THREE.Mesh(new THREE.BoxGeometry(),green),new THREE.Mesh(new THREE.BoxGeometry(),neutral))
 const before={h:0,s:0,l:0},after={h:0,s:0,l:0}
 green.color.getHSL(before)
 enhanceOverviewModelSaturation(root)
 green.color.getHSL(after)
 expect(after.s).toBeCloseTo(before.s*overviewSaturationScale,5)
 expect(after.l).toBeCloseTo(before.l,5)
 expect(neutral.color.getHexString()).toBe('a0a0a0')
 root.children.forEach(mesh=>{mesh.geometry.dispose();mesh.material.dispose()})
})

it('brightens only context building materials and keeps the tuned colors after floor restoration', () => {
 const root = new THREE.Group(), resources = new Set(), register = material => resources.add(material)
 const names = ['CTX_Building_White', 'CTX_Building_Light', 'CTX_Building_Mid', 'CTX_Roof', 'CTX_Road', 'M_GreenFacade', 'M_White']
 for (const name of names) {
  const material = new THREE.MeshStandardMaterial({ color: '#9CA2A6', roughness: .88 })
  material.name = name
  root.add(new THREE.Mesh(new THREE.BoxGeometry(), material))
 }
 applyOverviewArchitecturalMaterials(root, register)
 expect(root.children.slice(0, 4).map(mesh => mesh.material.color.getHexString())).toEqual(['ffffff', 'fcfcfa', 'f7f8f5', 'f0f2ee'])
 for (const mesh of root.children.slice(0, 4)) expect(mesh.material.emissiveIntensity).toBe(.42)
 for (const mesh of root.children.slice(4)) {
  expect(mesh.material.color.getHexString()).toBe('9ca2a6')
  expect(mesh.material.emissive.getHexString()).toBe('000000')
 }
 for (const mesh of root.children) expect(mesh.material.roughness).toBe(.88)
 const baseline = captureOverviewOriginalState(root, register)
 root.children[0].material.color.set('#111111')
 root.children[0].material.emissiveIntensity = 0
 restoreOverviewOriginalState(baseline)
 expect(root.children[0].material.color.getHexString()).toBe('ffffff')
 expect(root.children[0].material.emissiveIntensity).toBe(.42)
 resources.forEach(material => material.dispose())
 root.children.forEach(mesh => { mesh.geometry.dispose(); mesh.material.dispose() })
})
