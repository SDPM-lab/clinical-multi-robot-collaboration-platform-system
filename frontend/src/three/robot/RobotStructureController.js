import * as THREE from 'three'
import { componentIdForMesh, robotExplodedOffsets } from '../../config/robotComponentRules.js'

// Owns presentation-only state on the existing scene. Never creates a renderer.
export class RobotStructureController {
  constructor({ root, camera, controls, canvas, onSelect, canInteract, reducedMotion }) {
    Object.assign(this, { root, camera, controls, canvas, onSelect, canInteract, reducedMotion })
    this.mode = 'whole'; this.selected = null; this.hovered = null
    this.meshes = []; this.records = []; this.pointerIds = new Set()
    this.raycaster = new THREE.Raycaster()
    root.updateMatrixWorld(true)
    this.wholeBox = new THREE.Box3().setFromObject(root)
    const center = this.wholeBox.getCenter(new THREE.Vector3())
    const dimensions = this.wholeBox.getSize(new THREE.Vector3())
    const span = Math.max(dimensions.x, dimensions.y, dimensions.z)
    const parts = []
    root.traverse(mesh => {
      if (!mesh.isMesh) return
      parts.push({ mesh, center: new THREE.Box3().setFromObject(mesh).getCenter(new THREE.Vector3()) })
    })
    // Origins can be shared by unrelated GLB meshes. Use geometry bounds in world space.
    const lower = parts.filter(part => part.center.y < center.y - span * .25)
      .sort((a, b) => a.center.x - b.center.x || a.center.z - b.center.z)
    parts.sort((a, b) => b.center.y - a.center.y).forEach(({ mesh, center: partCenter }, index) => {
      const id = componentIdForMesh(mesh.name)
      mesh.userData.originalTransform = { position: mesh.position.clone(), quaternion: mesh.quaternion.clone(), scale: mesh.scale.clone() }
      const original = mesh.position.clone()
      const direction = partCenter.clone().sub(center)
      if (robotExplodedOffsets[mesh.name]) direction.set(...robotExplodedOffsets[mesh.name])
      if (direction.lengthSq() < 1e-10) direction.set(index % 2 ? 1 : -1, .25, index % 3 ? .4 : -.4)
      const offset = direction.normalize().multiplyScalar(span * (id === 'shell' ? .48 : .32))
      const rank = lower.findIndex(part => part.mesh === mesh)
      if (rank >= 0) {
        // Small bottom parts need distinct X/Y/Z lanes, not parallel downward rays.
        const lane = rank - (lower.length - 1) / 2
        offset.x = span * lane * .17
        if (Math.abs(partCenter.x - center.x) > span * .06) {
          offset.x = Math.sign(partCenter.x - center.x) * Math.max(Math.abs(offset.x), span * .2)
        }
        offset.y = -span * (.23 + rank * .075)
        offset.z = span * (rank % 2 ? .23 : -.23)
      }
      const exploded = mesh.parent.worldToLocal(mesh.parent.localToWorld(original.clone()).add(offset))
      this.meshes.push(mesh)
      this.records.push({ mesh, id, original, exploded, offset, delay: index * 65 })
    })
    this.applyExplosion(1)
    this.explodedBox = new THREE.Box3().setFromObject(root)
    this.applyExplosion(0)
    this.handlers = {
      pointerdown: e => { this.pointerIds.add(e.pointerId); if (this.pointerIds.size > 1) this.down = null; else this.down = { x:e.clientX, y:e.clientY, id:e.pointerId }; },
      pointermove: e => {
        if (this.down && Math.hypot(e.clientX-this.down.x,e.clientY-this.down.y)>5) this.down = null
        this.hovered = this.pointerIds.size ? null : this.hit(e)
        canvas.style.cursor = this.hovered ? 'pointer' : ''
      },
      pointerup: e => {
        const down = this.down
        this.pointerIds.delete(e.pointerId); this.down = null
        if (!down || down.id !== e.pointerId || Math.hypot(e.clientX-down.x,e.clientY-down.y)>5 || e.button !== 0) return
        const id = this.hit(e)
        if (id) this.select(id)
      },
      pointercancel: e => { this.pointerIds.delete(e.pointerId); this.down = null; this.hovered = null },
      pointerleave: () => { this.hovered = null; canvas.style.cursor = '' },
    }
    Object.entries(this.handlers).forEach(([name, handler]) => canvas.addEventListener(name, handler))
  }
  hit(event) {
    if (!this.canInteract() || this.focusTween || this.explodeTween) return null
    const rect = this.canvas.getBoundingClientRect()
    if (!rect.width || !rect.height) return null
    this.root.updateMatrixWorld(true)
    this.raycaster.setFromCamera(new THREE.Vector2((event.clientX-rect.left)/rect.width*2-1, -(event.clientY-rect.top)/rect.height*2+1), this.camera)
    // Include all surfaces for occlusion. Unclassified front surfaces block selection.
    const hits = this.raycaster.intersectObjects(this.records.map(r => r.mesh), false)
    const hit = hits.find(({object}) => this.mode !== 'xray' || componentIdForMesh(object.name) !== 'shell') || hits[0]
    return hit ? componentIdForMesh(hit.object.name) : null
  }
  select(id) {
    if (!this.canInteract() || !this.records.some(r => r.id === id)) return
    this.finishExplosion()
    this.selected = id; this.hovered = null
    this.root.updateMatrixWorld(true)
    const box = new THREE.Box3()
    this.records.filter(r => r.id === id).forEach(r => box.expandByObject(r.mesh))
    // Selection highlights the part without changing the camera or compressing the exploded view.
    this.onSelect(id)
  }
  applyExplosion(amount) {
    this.records.forEach(r => {
      r.mesh.position.lerpVectors(r.original,r.exploded,amount)
      r.mesh.quaternion.copy(r.mesh.userData.originalTransform.quaternion)
      r.mesh.scale.copy(r.mesh.userData.originalTransform.scale)
    })
    this.root.updateMatrixWorld(true)
  }
  applyEntrance(elapsed) {
    const ease = value => 1 - (1 - THREE.MathUtils.clamp(value, 0, 1)) ** 3
    this.records.forEach(record => {
      const expand = ease((elapsed - 250 - record.delay) / 700)
      const assemble = ease((elapsed - 1900 - record.delay) / 1100)
      const amount = this.reducedMotion() || elapsed >= 4100 ? 0 : expand * (1 - assemble)
      record.mesh.position.lerpVectors(record.original, record.exploded, amount)
      record.mesh.quaternion.copy(record.mesh.userData.originalTransform.quaternion)
      record.mesh.scale.copy(record.mesh.userData.originalTransform.scale)
    })
    this.root.updateMatrixWorld(true)
  }
  framing(box, part = null) {
    const {camera,controls} = this
    const target = box.getCenter(new THREE.Vector3())
    if(part) target.lerp(part.getCenter(new THREE.Vector3()), .18)
    const direction = camera.position.clone().sub(controls.target).normalize()
    const right = new THREE.Vector3().crossVectors(camera.up,direction).normalize()
    const up = new THREE.Vector3().crossVectors(direction,right).normalize()
    const rect = this.safeRect || {left:0,right:1,top:0,bottom:1}
    const tan = Math.tan(THREE.MathUtils.degToRad(camera.fov/2))
    const halfWidth = (rect.right-rect.left)*camera.aspect*tan / 1.25
    const halfHeight = (rect.bottom-rect.top)*tan / (this.mode==='exploded'?1.25:1.08)
    let distance = 0
    for(const x of [box.min.x,box.max.x]) for(const y of [box.min.y,box.max.y]) for(const z of [box.min.z,box.max.z]) {
      const delta = new THREE.Vector3(x,y,z).sub(target), depth=delta.dot(direction)
      distance=Math.max(distance,depth+Math.abs(delta.dot(right))/halfWidth,depth+Math.abs(delta.dot(up))/halfHeight)
    }
    // Whole bounds always constrain focus, including the smallest base meshes.
    const size=box.getSize(new THREE.Vector3())
    if(part) distance=Math.max(distance,Math.max(part.getSize(new THREE.Vector3()).length()*2.2,size.y*.58)/(2*tan))
    controls.minDistance=Math.max(size.length()*.65,distance*.85)
    controls.maxDistance=Math.max(12,distance*2)
    camera.near=.05; camera.far=Math.max(100,distance*8)
    return {position:target.clone().addScaledVector(direction,distance),target}
  }
  focusBox(part = null, immediate = false) {
    const box=this.mode==='exploded'?this.explodedBox:new THREE.Box3().setFromObject(this.root)
    const fit=this.framing(box,part)
    if(immediate) {this.camera.position.copy(fit.position);this.controls.target.copy(fit.target);this.camera.lookAt(fit.target)}
    else this.tweenCamera(fit.position,fit.target)
  }
  setSafeRect(rect, immediate=false) {
    this.safeRect=rect
    const next={x:(.5-(rect.left+rect.right)/2),y:(.5-(rect.top+rect.bottom)/2)}
    this.composition={from:this.offset || {x:0,y:0},to:next,start:performance.now(),immediate}
    this.focusBox(null,immediate)
    if(this.focusTween)this.focusTween.duration=450
  }
  tweenCamera(position, target) {
    // Drain OrbitControls damping before disabling it, avoiding a jump after focus.
    const damping = this.controls.enableDamping
    this.controls.enableDamping = false; this.controls.update(); this.controls.enableDamping = damping
    this.focusTween = { start:performance.now(), from:this.camera.position.clone(), targetFrom:this.controls.target.clone(), position, target }
  }
  returnWhole() {
    this.selected = null; this.hovered = null
    this.onSelect(null)
    this.focusBox()
  }
  setMode(mode) {
    if (!this.canInteract() || !['whole','xray','exploded'].includes(mode)) return
    this.mode = mode
    this.selected=null;this.hovered=null;this.onSelect(null)
    // Fit expanded bounds before a single mesh moves. Retraction keeps this safe distance.
    if(mode==='exploded') this.focusBox()
    this.explodeTween = {start:performance.now()+(mode==='exploded'&&!this.reducedMotion()?750:0), entries:this.records.map(r=>({...r,from:r.mesh.position.clone(),to:(mode==='exploded'?r.exploded:r.original).clone()}))}
  }
  finishExplosion() {
    if (!this.explodeTween) return
    this.explodeTween.entries.forEach(r => r.mesh.position.copy(r.to))
    this.explodeTween = null
  }
  objectsFor(id) {
    return id ? this.records.filter(record => record.id === id).map(record => record.mesh) : []
  }
  reset() {
    this.mode = 'whole'; this.selected = null; this.hovered = null; this.focusTween = null; this.explodeTween = null; this.focusAfterExplosion = null
    this.records.forEach(({mesh}) => {
      mesh.position.copy(mesh.userData.originalTransform.position)
      mesh.quaternion.copy(mesh.userData.originalTransform.quaternion)
      mesh.scale.copy(mesh.userData.originalTransform.scale)
    })
    this.controls.minDistance = 3.8; this.controls.maxDistance = 9
    this.canvas.style.cursor = ''; this.onSelect(null)
  }
  update(time) {
    const ease = t => 1-(1-t)**3
    if(this.composition) {
      const c=this.composition,t=c.immediate||this.reducedMotion()?1:Math.min(1,(time-c.start)/450)
      this.offset={x:THREE.MathUtils.lerp(c.from.x,c.to.x,ease(t)),y:THREE.MathUtils.lerp(c.from.y,c.to.y,ease(t))}
      const r=this.canvas.getBoundingClientRect()
      this.camera.setViewOffset(r.width,r.height,this.offset.x*r.width,this.offset.y*r.height,r.width,r.height)
      if(t===1)this.composition=null
    }
    if (this.explodeTween) {
      const elapsed = time - this.explodeTween.start
      let complete = true
      this.explodeTween.entries.forEach(r => {
        const t = this.reducedMotion() ? 1 : THREE.MathUtils.clamp((elapsed - r.delay) / 650, 0, 1)
        r.mesh.position.lerpVectors(r.from, r.to, ease(t))
        if (t < 1) complete = false
      })
      if (complete) {
        this.explodeTween.entries.forEach(r=>r.mesh.position.copy(r.to))
        this.explodeTween = null
        this.focusBox()
      }
    }
    if (this.focusTween) {
      const f = this.focusTween, t = this.reducedMotion()?1:Math.min(1,(time-f.start)/(f.duration || 750))
      this.camera.position.lerpVectors(f.from,f.position,ease(t))
      this.controls.target.lerpVectors(f.targetFrom,f.target,ease(t))
      this.camera.lookAt(this.controls.target)
      if(t===1)this.focusTween=null
    }
  }
  styleMaterial(mesh, material, original) {
    const id = componentIdForMesh(mesh.name)
    material.transparent = original.transparent
    material.opacity = original.opacity
    material.depthWrite = original.depthWrite
    if (this.mode === 'xray' && id === 'shell') {
      material.transparent = true
      material.opacity = .27
      material.depthWrite = false
      return
    }
    const palette = ['#ec9d6f', '#74b9ad', '#ddbd72', '#8baacb', '#b1a0c6', '#79a8bf', '#cba784', '#a4bb83']
    const index = this.records.findIndex((record) => record.mesh === mesh)
    if (this.mode === 'exploded' && index >= 0) {
      material.color.lerp(new THREE.Color(palette[index % palette.length]), .4)
    }
    if (this.selected === id) {
      material.color.lerp(new THREE.Color('#ed8753'), .58)
      material.emissive?.set('#a6401f')
      material.emissiveIntensity = Math.max(material.emissiveIntensity || 0, .32)
    } else if (this.hovered === id) {
      material.color.lerp(new THREE.Color('#64b7a5'), .36)
    } else if (this.selected) {
      material.color.lerp(new THREE.Color('#aab2ae'), .16)
    }
  }
  dispose() {
    Object.entries(this.handlers).forEach(([name,handler])=>this.canvas.removeEventListener(name,handler))
    this.composition = null; this.down = null; this.records = []; this.meshes = []; this.pointerIds.clear(); this.focusTween = null; this.explodeTween = null
  }
}
