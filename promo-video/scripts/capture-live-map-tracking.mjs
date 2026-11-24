import assert from 'node:assert/strict';
import {mkdir,readFile,writeFile} from 'node:fs/promises';

const playwright = process.env.MEDISYNC_PLAYWRIGHT || '/tmp/medisync-capture/node_modules/playwright/index.mjs';
const {chromium} = await import(playwright);
const output=process.env.MEDISYNC_LIVE_FRAMES || '/tmp/medisync-live-frames';
const origin='http://127.0.0.1:4194';
const demo=JSON.parse(await readFile(new URL('../src/ppo-scheduling-demo.json',import.meta.url)));
const robotId='robot-hospital_robot_3';
const task={id:demo.taskId,taskCode:demo.taskCode,taskType:demo.taskType,source:demo.source,destination:demo.destination,
  scheduledAt:demo.scheduledAt,createdAt:'2026-11-21T06:40:00Z',priority:demo.priority,assignedRobot:robotId,status:'running',isSimulated:true};
const robots=demo.robots.map((r,i)=>({id:`robot-hospital_robot_${i+1}`,name:r.id,levelName:'L1',
  hasTelemetry:false,battery:r.battery,status:r.id==='M01'?'執行任務中':r.status==='charging'?'充電中':'待命',modelAssetKey:'AGIBOT_A2D'}));
await mkdir(output,{recursive:true});
const browser=await chromium.launch({executablePath:process.env.MEDISYNC_CHROMIUM||'/tmp/chromium',args:['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
try{
 const page=await browser.newPage({viewport:{width:1280,height:720},locale:'en-US',timezoneId:'Asia/Taipei'});
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
         const startCamera = camera.position.clone();
         const startTarget = controls.target.clone();
         let view = null;
         let elapsed = 0;
         const baseFov = camera.fov;
         const frameState = (f) => {
           const smooth = (a,b) => {const p=THREE.MathUtils.clamp((f-a)/(b-a),0,1);return p*p*(3-2*p);};
           const progress = smooth(139,340);
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
             const amount=THREE.MathUtils.smoothstep(smooth(70,143),object.userData.routeRevealOffset*.72, object.userData.routeRevealOffset*.72+.28);
             const materials=Array.isArray(object.material)?object.material:[object.material];
             for(const material of materials)material.opacity=material.userData.baseOpacity*amount;
           }
           route.arrowGroup.visible=f>=143&&f<341;
           const track=smooth(145,177)*(1-smooth(251,292));
           const directional=forward.lengthSq()>.1?forward:new THREE.Vector3(0,0,1);
           const follow=getRobotCameraPose('thirdPerson',position,directional);
           follow.position.add(new THREE.Vector3(0,.5,0));
           const viewTarget=startTarget.clone().lerp(begin.clone().lerp(end,.5),.30*smooth(50,115));
           const wide=startCamera.clone().lerp(viewTarget,.065*smooth(1,58)+.065*smooth(60,121));
           const desiredPosition=wide.lerp(follow.position,track);
           const desiredTarget=viewTarget.lerp(follow.target,track);
           if(!view) view={position:desiredPosition.clone(),target:desiredTarget.clone()};
           view.position.lerp(desiredPosition,1-Math.exp(-11/30));
           view.target.lerp(desiredTarget,1-Math.exp(-11/30));
           camera.position.copy(view.position); camera.fov=baseFov;
           camera.updateProjectionMatrix(); camera.lookAt(view.target); camera.updateMatrixWorld(true);
           controls.target.copy(view.target);
           if(doorController)doorController.update(1/30,[position]);
           roomLabelLayer?.setVisible(track<.43);
           roomLabelLayer?.update();
           locationMarkerLayer?.setVisible(false);
           navigationLayer.robotControllers.forEach((candidate,id)=>{if(id!==actorId)candidate.wrapper.visible=false;});
           if(actorGroup)actorGroup.visible=false;
           showRunningTasks.value=f>=128 && track<.4;
           selectedRobotId.value=f>=360?actorId:null;
           elapsed=f;
           const project=(p,y)=>{const s=p.clone().setY(y).project(camera);return [(s.x*.5+.5)*1280,(.5-s.y*.5)*720];};
           return {frame:elapsed,progress,position:position.toArray(),camera:camera.position.toArray(),
             source:project(begin,.17),destination:project(end,.17),robot:project(position,controller.boundsHeight+.28)};
         };
         window.filmMap = {
           metadata:()=>({route:navigationLayer.routeEntries.find(row=>row.route.robotId===actorId).route.vertexIds,
              path:controller.points.map(p=>p.toArray()),length:controller.totalDistance,
              robotAsset:controller.modelAssetKey,cameraModes:['global','thirdPerson','firstPerson','localFollow']}),
           draw:(f,render)=>{
             const state=frameState(f);
             if(render)renderer.render(scene,camera);
             return state;
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
 const cdp=await page.context().newCDPSession(page);
 const stop=Number(process.env.MEDISYNC_LIVE_STOP||419);
 const stride=Number(process.env.MEDISYNC_LIVE_STRIDE||4);
 const states={};
 for(let f=0;f<=stop;f++){
   const render=f%stride===0||[59,60,149,150,269,270,339,340,359,360,419].includes(f)||f===stop;
   const state=await page.evaluate(([f,render])=>window.filmMap.draw(f,render),[f,render]);
   states[f]=state;
   if(!render)continue;
   const {data}=await cdp.send('Page.captureScreenshot',{format:'jpeg',quality:94,fromSurface:true});
   await writeFile(`${output}/${f}.jpg`,Buffer.from(data,'base64'));
   states[f]=state;
   if(f%60===0)console.log('Captured',f);
 }
 await writeFile(`${output}/metadata.json`,JSON.stringify({meta,states,blocked:sent},null,2));
} finally {await browser.close();}
