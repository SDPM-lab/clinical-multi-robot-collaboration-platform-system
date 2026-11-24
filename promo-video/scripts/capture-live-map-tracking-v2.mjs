import assert from 'node:assert/strict';
import {mkdir,readFile,writeFile} from 'node:fs/promises';

const playwright = process.env.MEDISYNC_PLAYWRIGHT || '/tmp/medisync-capture/node_modules/playwright/index.mjs';
const {chromium} = await import(playwright);
const output=process.env.MEDISYNC_LIVE_FRAMES || '/tmp/medisync-live-v2-buffer';
const origin='http://127.0.0.1:4194';
const demo=JSON.parse(await readFile(new URL('../src/ppo-scheduling-demo.json',import.meta.url)));
const robotId='robot-hospital_robot_3';
const task={id:demo.taskId,taskCode:demo.taskCode,taskType:demo.taskType,source:demo.source,destination:demo.destination,
  scheduledAt:demo.scheduledAt,createdAt:'2026-11-21T06:40:00Z',priority:demo.priority,assignedRobot:robotId,status:'running',isSimulated:true};
const robots=demo.robots.map((r,i)=>({id:`robot-hospital_robot_${i+1}`,name:r.id,levelName:'L1',
  hasTelemetry:false,battery:r.battery,status:r.id==='M01'?'執行任務中':r.status==='charging'?'充電中':'待命',modelAssetKey:'AGIBOT_A2D'}));
await mkdir(output,{recursive:true});
const browser=await chromium.launch({executablePath:process.env.MEDISYNC_CHROMIUM||'/tmp/chromium',args:['--no-sandbox','--use-gl=angle','--use-angle=vulkan','--enable-features=Vulkan','--ignore-gpu-blocklist']});
try{
 const page=await browser.newPage({viewport:{width:1920,height:1080},locale:'en-US',timezoneId:'Asia/Taipei'});
 await page.addInitScript(()=>{
   localStorage.setItem('hospital-rmf-locale','en');
   let seed=7741;
   Math.random=()=>((seed=(Math.imul(1664525,seed)+1013904223)>>>0)/4294967296);
 });
 await page.clock.setFixedTime(new Date(demo.scheduledAt));
 await page.routeWebSocket('**/*',ws=>{if(new URL(ws.url()).host==='127.0.0.1:4194')ws.connectToServer();else ws.close();});
 const sent=[];
 await page.route('**/*',async route=>{
   const url=new URL(route.request().url()); const method=route.request().method();
   const reply=json=>route.fulfill({json,headers:{'access-control-allow-origin':origin,'access-control-allow-credentials':'true'}});
   if(url.pathname==='/api/auth/me'&&method==='GET')return reply({id:'demo',name:'MediSync Demo',email:'demo@example.invalid'});
   if(url.pathname==='/api/auth/csrf'&&method==='GET')return reply({token:'live-map-film'});
   if(url.pathname==='/api/robots'&&method==='GET')return reply({robots,connection:'connected'});
   if(url.pathname==='/api/v1/task'&&method==='GET')return reply([task]);
   if(url.origin!==origin||method!=='GET'||url.pathname.startsWith('/api/')){sent.push([method,url.pathname]);return route.abort();}
   if(url.pathname.endsWith('/HospitalScene.vue')&&(!url.search||url.searchParams.has('t'))){
     const response=await route.fetch();
     let code=await response.text();
     const marker='const delta = sceneClock.getDelta()';
     assert(code.includes(marker),'HospitalScene capture hook missing');
     code=code.replace(marker,`
       const actorId = ${JSON.stringify(robotId)};
       const controller = navigationLayer?.robotControllers.get(actorId);
       if (controller?.model && controller.totalDistance > 0 && !window.filmMap) {
         renderer.shadowMap.enabled = false;
         navigationLayer.robotControllers.forEach((candidate,id)=>{if(id!==actorId) candidate.wrapper.visible = false;});
         scene.traverse(o=>{ if(o.isLight)o.castShadow=false; });
         renderer.setPixelRatio(1);
         renderer.setClearColor(0xe9eceb,1);
         renderer.setSize(1920,1080,false);
         camera.aspect = 1920/1080;
         const startTarget = controls.target.clone();
         const originalOffset = camera.position.clone().sub(startTarget);
         const wideOffset = originalOffset.clone().multiplyScalar(1.36);
         const baseFov = camera.fov;
         let followView = null;
         const ease = (f,a,b) => {const p=THREE.MathUtils.clamp((f-a)/(b-a),0,1);return p*p*p*(10+p*(-15+6*p));};
         const frameState = (f) => {
           const progress = ease(f,198,397);
           controller.distance=controller.totalDistance*progress;
           controller.speed=0;
           controller.entranceAge=1.5;
           controller.wrapper.scale.setScalar(1);
           navigationLayer.update(1/30);
           const position=controller.getWorldPosition();
           const forward=controller.getForwardVector();
           const route = navigationLayer.routeEntries.find(row=>row.route.robotId===actorId);
           const begin=controller.points[0], end=controller.points.at(-1);
           for (const object of route.revealObjects) {
             const amount=THREE.MathUtils.smoothstep(ease(f,107,157),object.userData.routeRevealOffset*.72, object.userData.routeRevealOffset*.72+.28);
             const materials=Array.isArray(object.material)?object.material:[object.material];
             for(const material of materials)material.opacity=material.userData.baseOpacity*amount;
           }
           route.arrowGroup.visible=false;
           const desired=getRobotCameraPose('thirdPerson',position,forward);
           desired.position.y+=.5;
           if(!followView)followView={position:desired.position.clone(),target:desired.target.clone()};
           followView.position.lerp(desired.position,.26);
           followView.target.lerp(desired.target,.26);
           if(doorController)doorController.update(1/30,[position]);
           locationMarkerLayer?.setVisible(false);
           roomLabelLayer?.setVisible(false);
           if(actorGroup)actorGroup.visible=false;
           navigationLayer.robotControllers.forEach((candidate,id)=>{if(id!==actorId)candidate.wrapper.visible=false;});
           const wide=wideOffset.clone().multiplyScalar(1-.045*ease(f,0,24)).add(startTarget);
           const local=getRobotCameraPose('localFollow',position,forward);
           const apply=(pose)=>{
             camera.position.copy(pose.position); camera.fov=baseFov;
             camera.updateProjectionMatrix(); camera.lookAt(pose.target);camera.updateMatrixWorld(true);
           };
           const project=(p,y)=>{const s=p.clone().setY(y).project(camera);return [(s.x*.5+.5)*1920,(.5-s.y*.5)*1080];};
           apply({position:wide,target:startTarget});
           const state={frame:f,progress,position:position.toArray(),camera:camera.position.toArray(),
             target:startTarget.toArray(),follow:followView.position.toArray(),followTarget:followView.target.toArray(),
             local:local.position.toArray(),localTarget:local.target.toArray(),
             source:project(begin,.17),destination:project(end,.17),robot:project(position,controller.boundsHeight+.22)};
           const capture=pose=>{
             apply(pose);
             renderer.render(scene,camera);
             return renderer.domElement.toDataURL('image/jpeg',.98).split(',')[1];
           };
           return {state,capture,wide:{position:wide,target:startTarget},local,follow:followView};
         };
         let latestFrame=-1;
         let sample;
         window.filmMap = {
           metadata:()=>({route:navigationLayer.routeEntries.find(row=>row.route.robotId===actorId).route.vertexIds,
              path:controller.points.map(p=>p.toArray()),length:controller.totalDistance,
              robotAsset:controller.modelAssetKey,buffer:[renderer.domElement.width,renderer.domElement.height],
              sourceModes:['global','thirdPerson','localFollow']}),
           draw:(f,main,second)=>{
             if(f!==latestFrame){sample=frameState(f);latestFrame=f;}
             const mode=f<204||f>=360?'wide':f<322?'follow':'local';
             return {state:sample.state,
               image:main?sample.capture(sample[mode]):null,
               secondary:second?sample.capture(sample.local):null};
           }
         };
         return;
       }
       if(window.filmMap)return;
       ${marker}`);
     return route.fulfill({response,body:code});
   }
   return route.continue();
 });
 page.on('pageerror',e=>console.error(e));
 page.on('console',m=>{if(m.type()==='error')console.error(m.text());});
 await page.goto(origin+'/?mapCameraDebug=1',{waitUntil:'domcontentloaded',timeout:90000});
 await page.addStyleTag({content:'vite-plugin-vue-devtools,#vue-devtools__anchor,.map-camera-debug,.follow-debug{display:none!important} *,*::before,*::after{animation-duration:.001s!important;transition-duration:.001s!important}'});
 await page.waitForFunction(()=>Boolean(window.filmMap),{},{timeout:150000});
 const meta=await page.evaluate(()=>window.filmMap.metadata());
 assert(meta.route.length>1);
 console.log(JSON.stringify(meta));
 const stop=Number(process.env.MEDISYNC_LIVE_STOP||449);
 const states=[];
 for(let f=0;f<=stop;f++){
   const main=f<=24||(f>=108&&f<=158)||(f>=197&&f<=401)||f===stop;
   const second=f>=270&&f<322;
   const {state,image,secondary}=await page.evaluate(([f,main,second])=>window.filmMap.draw(f,main,second),[f,main,second]);
   if(image)await writeFile(`${output}/${f}.jpg`,Buffer.from(image,'base64'));
   if(secondary)await writeFile(`${output}/local-${f}.jpg`,Buffer.from(secondary,'base64'));
   states.push(state);
   if(f%15===0)console.log('Captured',f);
 }
 await writeFile(`${output}/metadata.json`,JSON.stringify({meta,states,blocked:sent},null,2));
} finally {await browser.close();}
