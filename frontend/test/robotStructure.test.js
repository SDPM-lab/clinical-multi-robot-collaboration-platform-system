import { afterEach, describe, expect, it, vi } from 'vitest'
import { readFileSync } from 'node:fs'
import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { RobotStructureController } from '@/three/robot/RobotStructureController.js'
import { robotPresentation } from '@/config/robotHmi.js'
import { robotComponentRules } from '@/config/robotComponentRules.js'
const cleanup=[]
afterEach(()=>{cleanup.splice(0).forEach(f=>f());vi.restoreAllMocks()})
async function setup(){
  const bytes=readFileSync('public/models/robot.glb')
  const model=(await new GLTFLoader().parseAsync(new Uint8Array(bytes).buffer,'')).scene
  const box=new THREE.Box3().setFromObject(model), size=box.getSize(new THREE.Vector3()), center=box.getCenter(new THREE.Vector3())
  const root=new THREE.Group();root.add(model);root.scale.setScalar(2.8/size.y);root.position.copy(center).multiplyScalar(-2.8/size.y)
  const camera=new THREE.PerspectiveCamera(30,1,.01,100);camera.position.set(...robotPresentation.camera)
  const controls={target:new THREE.Vector3(0,.08,0),enableDamping:true,update:()=>{},minDistance:3.8,maxDistance:9}
  camera.lookAt(controls.target);camera.updateMatrixWorld()
  const canvas=document.createElement('canvas');canvas.getBoundingClientRect=()=>({left:0,top:0,width:600,height:600})
  let enabled=true
  const onSelect=vi.fn()
  const controller=new RobotStructureController({root,camera,controls,canvas,onSelect,canInteract:()=>enabled,reducedMotion:()=>false})
  cleanup.push(()=>{controller.dispose();model.traverse(m=>{if(m.isMesh){m.geometry.dispose();m.material.dispose()}})})
  return {controller,root,camera,controls,canvas,onSelect,setEnabled:value=>{enabled=value}}
}
describe('real GLB structure inspection',()=>{
  it('maps only verified meshes and restores exploded positions without accumulated drift',async()=>{
    const {controller:c}=await setup()
    expect(c.records).toHaveLength(8)
    expect(c.meshes).toHaveLength(8)
    expect(robotComponentRules.battery).toEqual([])
    expect(robotComponentRules.leftMotor).toEqual([])
    for(let i=0;i<3;i++){
      c.setMode('exploded');c.update(performance.now()+1800)
      expect(c.records.every(r=>!r.mesh.position.equals(r.original))).toBe(true)
      c.setMode('whole');c.update(performance.now()+1800)
      c.records.forEach(r=>expect(r.mesh.position.distanceTo(r.original)).toBeLessThan(1e-9))
    }
    c.reset();expect(c.mode).toBe('whole');expect(c.selected).toBeNull()
  })
  it('highlights selected meshes without zooming into the part',async()=>{
    const {controller:c,camera,controls,setEnabled}=await setup()
    setEnabled(false);c.select('chassis');expect(c.selected).toBeNull()
    setEnabled(true)
    const before=camera.position.clone(), targetBefore=controls.target.clone()
    c.select('chassis')
    expect(c.focusTween).toBeUndefined()
    expect(camera.position.equals(before)).toBe(true)
    expect(controls.target.equals(targetBefore)).toBe(true)
    const chosen=c.records.find(r=>r.id==='chassis'),shell=c.records.find(r=>r.id==='shell')
    const mat=chosen.mesh.material.clone();c.styleMaterial(chosen.mesh,mat,chosen.mesh.material)
    expect(mat.color.getHex()).not.toBe(chosen.mesh.material.color.getHex())
    expect(mat.map).toBe(chosen.mesh.material.map);mat.dispose()
    const faded=shell.mesh.material.clone();c.styleMaterial(shell.mesh,faded,shell.mesh.material)
    expect(faded.opacity).toBe(1);expect(faded.color.getHex()).not.toBe(shell.mesh.material.color.getHex());faded.dispose()
    c.reset();c.setMode('xray')
    const xray=shell.mesh.material.clone();c.styleMaterial(shell.mesh,xray,shell.mesh.material);expect(xray.opacity).toBe(.27);xray.dispose()
  })
  it('keeps every whole-model corner in the overlay safe area when focusing tiny parts or exploding',async()=>{
    const {controller:c,camera,canvas}=await setup()
    canvas.getBoundingClientRect=()=>({left:0,top:0,width:1536,height:704})
    camera.aspect=1536/704
    c.setSafeRect({left:.21,right:.69,top:.14,bottom:.98},true)
    c.update(performance.now()+1000)
    for(const mode of ['whole','exploded']) {
      c.setMode(mode);c.update(performance.now()+2000);c.update(performance.now()+3000)
      for(const id of ['display','chassis','baseCenter','lowerFront']) {
        c.select(id);c.update(performance.now()+4000);camera.updateMatrixWorld()
        const box=new THREE.Box3().setFromObject(c.root)
        for(const x of [box.min.x,box.max.x])for(const y of [box.min.y,box.max.y])for(const z of [box.min.z,box.max.z]) {
          const p=new THREE.Vector3(x,y,z).project(camera)
          expect((p.x+1)/2).toBeGreaterThanOrEqual(.21)
          expect((p.x+1)/2).toBeLessThanOrEqual(.69)
          expect((1-p.y)/2).toBeGreaterThanOrEqual(.14)
          expect((1-p.y)/2).toBeLessThanOrEqual(.98)
        }
      }
    }
  })
  it('raycasts verified components, ignores drag gestures and removes listeners',async()=>{
    const {controller:c,canvas,onSelect}=await setup()
    const hit=c.records.find(r=>r.id==='display').mesh
    vi.spyOn(c.raycaster,'intersectObjects').mockReturnValue([{object:hit}])
    const event=(type,x)=>{const e=new MouseEvent(type,{clientX:x,clientY:100,button:0});Object.defineProperty(e,'pointerId',{value:1});canvas.dispatchEvent(e)}
    event('pointerdown',100);event('pointermove',130);event('pointerup',130)
    expect(onSelect).not.toHaveBeenCalled()
    event('pointerdown',100);event('pointerup',100);expect(onSelect).toHaveBeenCalledWith('display')
    const remove=vi.spyOn(canvas,'removeEventListener');c.dispose();expect(remove).toHaveBeenCalledTimes(5)
  })
})

it('separates bottom meshes in three axes and staggers entrance without changing geometry or materials', async () => {
 const { controller:c } = await setup()
 const originals = c.records.map(r => ({ geometry:r.mesh.geometry, material:r.mesh.material, transform:r.mesh.userData.originalTransform }))
 const lower = c.records.filter(r => ['chassis','baseCenter','baseRear','lowerFront','lowerInner'].includes(r.id))
 expect(new Set(lower.map(r=>r.offset.x.toFixed(3))).size).toBeGreaterThan(2)
 expect(new Set(lower.map(r=>r.offset.y.toFixed(3))).size).toBeGreaterThan(2)
 expect(lower.some(r=>r.offset.z>0)).toBe(true)
 expect(lower.some(r=>r.offset.z<0)).toBe(true)
 c.applyEntrance(310)
 expect(c.records[0].mesh.position.equals(c.records[0].original)).toBe(false)
 expect(c.records.at(-1).mesh.position.equals(c.records.at(-1).original)).toBe(true)
 for (let repeat=0;repeat<3;repeat++) {
  c.applyEntrance(1700)
  c.applyEntrance(4100)
  c.records.forEach((r,i)=>{
   expect(r.mesh.position.equals(originals[i].transform.position)).toBe(true)
   expect(r.mesh.quaternion.equals(originals[i].transform.quaternion)).toBe(true)
   expect(r.mesh.scale.equals(originals[i].transform.scale)).toBe(true)
   expect(r.mesh.geometry).toBe(originals[i].geometry)
   expect(r.mesh.material).toBe(originals[i].material)
  })
 }
 c.reducedMotion=()=>true
 c.applyEntrance(1500)
 expect(c.records.every(r=>r.mesh.position.equals(r.original))).toBe(true)
})
