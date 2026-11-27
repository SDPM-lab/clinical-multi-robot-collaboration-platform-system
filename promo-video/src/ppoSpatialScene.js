import * as T from "three";
import {mergeGeometries} from "three/addons/utils/BufferGeometryUtils.js";
import {GLTFLoader} from "three/addons/loaders/GLTFLoader.js";
import {poseAgibotMapArms} from "./posePpoMapArms";
import docks from "./ppo-spatial-docks.json";

const v=(x=0,y=0,z=0)=>new T.Vector3(x,y,z);
const ease=(f,a,b)=>{
  const t=T.MathUtils.clamp((f-a)/(b-a),0,1);
  return t*t*t*(10+t*(-15+6*t));
};
const dock=(name)=>v(...docks[name]);
const blend=(a,b,t)=>a.clone().lerp(b,t);
const cameraOffset=(angle,elevation)=>v(Math.sin(angle)*30,elevation,Math.cos(angle)*30);
const candidateSpecs=[
  ["M01","pharmacy_dock",0,0],["M02","ward_a_dock",0,0],
  ["C01","laboratory_dock",0,0],["C02","nurse_station_dock",0,0],
  ["W01","charging_dock",-.54,-.35],["W02","charging_dock",.12,.27],["W03","charging_dock",.65,-.35],
];

// Flatten identical materials after the product pose is applied. Position,
 // normals, UVs and vertex colors remain from the original GLB.
function batchStatic(root){
  root.updateMatrixWorld(true);
  const group=new T.Group();
  const buckets=new Map();
  const pass=(object)=>{
    if(!object.visible)return;
    if(object.isMesh && !Array.isArray(object.material) && !object.isSkinnedMesh){
      const source=object.geometry;
      const key=object.material.uuid+"/"+Object.keys(source.attributes).sort().join(",");
      const geometry=(source.index?source.toNonIndexed():source.clone()).applyMatrix4(object.matrixWorld);
      const bucket=buckets.get(key)??{material:object.material,geometries:[]};
      bucket.geometries.push(geometry);
      buckets.set(key,bucket);
    }
    for(const child of object.children)pass(child);
  };
  pass(root);
  for(const {material,geometries} of buckets.values()){
    const merged=mergeGeometries(geometries);
    if(merged){
      group.add(new T.Mesh(merged,material));
      geometries.forEach(g=>g.dispose());
    }else{
      for(const g of geometries)group.add(new T.Mesh(g,material));
    }
  }
  return group;
}

export async function makePpoScene(canvas,url){
  const renderer=new T.WebGLRenderer({canvas,alpha:true,antialias:true,preserveDrawingBuffer:true});
  renderer.setSize(760,449,false);
  renderer.setPixelRatio(1);
  renderer.setClearColor(0xfaf6f0,0);
  renderer.toneMapping=T.ACESFilmicToneMapping;
  renderer.toneMappingExposure=1.08;
  const scene=new T.Scene();
  scene.add(new T.HemisphereLight(0xfff6ea,0x73839b,2.1));
  const key=new T.DirectionalLight(0xfff0df,2.4);key.position.set(-8,21,13);scene.add(key);
  const rim=new T.DirectionalLight(0xdce7ff,1.1);rim.position.set(7,11,-9);scene.add(rim);
  const camera=new T.OrthographicCamera(-10,10,6,-6,.1,250);
  const loader=new GLTFLoader();
  const [floorAsset,robotAsset]=await Promise.all([
    loader.loadAsync(url("L1__flat.glb")),loader.loadAsync(url("AGIBOT_A2D.glb")),
  ]);
  const floorModel=floorAsset.scenes.find(s=>s.name==="L1_Solid_Block_Map_v5")??floorAsset.scene;
  floorModel.traverse(o=>{
    if(o.isCamera||o.isLight||/^(Route(?:Node)?_|Preview_Ground|Label_)/.test(o.name))o.visible=false;
  });
  const floor=batchStatic(floorModel);
  scene.add(floor);
  poseAgibotMapArms(robotAsset.scene);
  const body=new T.Group();
  const box=new T.Box3().setFromObject(robotAsset.scene);
  const center=box.getCenter(v());
  robotAsset.scene.position.sub(v(center.x,box.min.y,center.z));
  body.add(batchStatic(robotAsset.scene));
  const unit=1.35/box.getSize(v()).y;
  body.scale.setScalar(unit);
  const muted=new T.MeshStandardMaterial({color:0x9aa0a5,roughness:.64});
  const bots=candidateSpecs.map(([id,name,dx,dz])=>{
    const obj=body.clone(true);
    const p=dock(name).add(v(dx,0,dz));
    obj.position.copy(p);
    scene.add(obj);
    return {id,obj,p,active:id.startsWith("M"), mutedParts:[]};
  });
  for(const bot of bots){
    if(bot.active)continue;
    bot.obj.traverse(o=>{
      if(o.isMesh)bot.mutedParts.push([o,o.material]);
    });
  }
  const hero=body.clone(true);
  scene.add(hero);
  const plates=new T.Group();
  scene.add(plates);
  const layouts=[[41,9,0xd46129],[35,7,0x656d78],[22,7,0xab8269]];
  const matrix=layouts.map(([count,columns,color],i)=>{
    const g=new T.Group();
    plates.add(g);
    const plate=new T.Mesh(new T.BoxGeometry(4.42,.11,2.72),new T.MeshStandardMaterial({color:0xded7cd,roughness:.62}));
    g.add(plate);
    const geometry=new T.BoxGeometry(.253,.076,.27);
    const material=new T.MeshStandardMaterial({color,roughness:.48});
    for(let n=0;n<count;n++){
      const cell=new T.Mesh(geometry,material);
      cell.position.set(-1.68+n%columns*.403,.09,-.88+Math.floor(n/columns)*.425);
      g.add(cell);
    }
    g.position.y=1.18-i*.68;
    return g;
  });

  let lastFrame=-1, cached={};
  function draw(inputFrame){
    let frame=inputFrame;
    if(frame>=58&&frame<90)frame=58;
    if(frame>=148&&frame<180)frame=148;
    if(frame>=231&&frame<300)frame=231;
    if(frame>=368&&frame<390)frame=368;
    if(frame>=433)frame=433;
    if(frame===lastFrame)return cached;
    lastFrame=frame;
    const world=frame<180||frame>=390;
    const opening=frame<90;
    const isMatrix=frame>=180&&frame<300;
    const isHero=frame>=300&&frame<390;
    floor.visible=world;
    floor.position.y=0;
    const eligible=ease(frame,121,147);
    for(const bot of bots){
      bot.obj.visible=world&&!opening&&(frame<180||bot.id==="M01");
      for(const [mesh,material] of bot.mutedParts)mesh.material=eligible>.55?muted:material;
    }
    hero.visible=isHero;
    plates.visible=isMatrix;
    let target=v(.5,.08,-.5), angle=.40, elevation=33, span=48;
    if(opening){
      const t=ease(frame,7,58);
      elevation=T.MathUtils.lerp(20,33,t);
      angle=T.MathUtils.lerp(.31,.40,t);
      span=T.MathUtils.lerp(45,50,t);
    }else if(frame<180){
      const t=ease(frame,96,148);
      angle=T.MathUtils.lerp(.4,.50,t);
      span=T.MathUtils.lerp(50,47.5,t);
    }else if(isMatrix){
      const t=ease(frame,198,231);
      target=v(0,.42,0);
      angle=.52; elevation=26;span=7.8;
      for(const [i,g] of matrix.entries()){
        g.position.y=(1.44-i*.92)*(1-.38*t);
        g.position.x=(i-1)*.35*(1-t);
      }
    }else if(isHero){
      const t=ease(frame,310,368);
      target=v(0,.68,0);
      angle=T.MathUtils.lerp(.96,.55,t);
      elevation=T.MathUtils.lerp(12,10,t);
      span=3.62;
    }else{
      const t=ease(frame,392,433);
      target=blend(dock("pharmacy_dock").add(v(0,.68,0)),v(8,.25,6),t);
      angle=T.MathUtils.lerp(.55,.48,t);
      elevation=T.MathUtils.lerp(10,30,t);
      span=T.MathUtils.lerp(3.62,18.5,t);
      // Lift the site into view under the stationary, orientation-matched robot.
      floor.position.y=-3*(1-ease(frame,390,407));
    }
    camera.position.copy(target).add(cameraOffset(angle,elevation));
    camera.lookAt(target);
    camera.left=-span/2;camera.right=span/2;
    camera.top=span*620/2100;camera.bottom=-camera.top;
    camera.updateProjectionMatrix();
    renderer.render(scene,camera);
    const points={};
    if(opening){
      for(const [name,id] of [["Pharmacy","pharmacy_dock"],["Ward A","ward_a_dock"],["Nurse Station","nurse_station_dock"]]){
        points[name]=dock(id).project(camera).toArray();
      }
    }else if(world){
      for(const b of bots)if(b.obj.visible)points[b.id]=b.p.clone().add(v(0,1.43,0)).project(camera).toArray();
    }
    cached=points;
    return points;
  }
  return {draw, dispose:()=>renderer.dispose()};
}
