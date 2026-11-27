import assert from "node:assert/strict";
import {createRequire} from "node:module";
import {mkdir,readFile,writeFile} from "node:fs/promises";
import {resolve} from "node:path";
import {PPO_TASK_WAYPOINT_IDS} from "../../frontend/src/config/dispatchDestinations.js";
import {scheduleContext} from "./task-creation-v4-fixture.mjs";
import {scenario} from "./task-creation-demo.mjs";
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.CAPTURE_DEPENDENCIES?resolve(process.env.CAPTURE_DEPENDENCIES,"node_modules/playwright"):"playwright");
const hiDpi=process.argv.includes("--phase-vnext");
const v6=hiDpi||process.argv.includes("--v6");
const v4=v6||process.argv.includes("--v4");
const context=v6?scheduleContext.map(task=>task.taskCode==="T0171"?
   {...task,scheduledAt:"2026-11-21T14:45:00+08:00"}:task):scheduleContext;
const out=new URL(hiDpi?"../public/task-creation-phase-vnext/":v6?"../public/task-creation-v6/":v4?"../public/task-creation-v4/":"../public/task-creation/",import.meta.url);
await mkdir(out,{recursive:true});
const origin="http://127.0.0.1:4179";
const browser=await chromium.launch({executablePath:process.env.CAPTURE_CHROMIUM,
 args:["--no-sandbox","--use-gl=angle","--use-angle=swiftshader","--enable-unsafe-swiftshader"]});
try {
 const page=await browser.newPage({viewport:{width:1600,height:900},deviceScaleFactor:hiDpi?2:1,locale:"en-US",timezoneId:"Asia/Taipei",reducedMotion:"reduce"});
 await page.addInitScript(()=>{
   localStorage.setItem("hospital-rmf-locale","en");
   const raf=requestAnimationFrame.bind(window);
   let last=0;
   window.requestAnimationFrame=callback=>raf(function paced(time){
     if(callback.name==="animate" && time-last<120) {raf(paced);return;}
     if(callback.name==="animate") last=time;
     callback(time);
   });
 });
 await page.clock.setFixedTime(new Date(scenario.now));
 let task, createReply;
 const events=[];
 let failure;
 await page.route("**/*",async route=>{
  const url=new URL(route.request().url()), method=route.request().method();
  const reply=json=>route.fulfill({json,headers:{"access-control-allow-origin":origin,"access-control-allow-credentials":"true"}});
  if(url.pathname==="/api/auth/me"&&method==="GET")return reply({id:"film-task",name:"MediSync Demo",email:"demo@example.invalid"});
  if(url.pathname==="/api/auth/csrf"&&method==="GET")return reply({token:"scene-two"});
  if(url.pathname==="/api/v1/place"&&method==="GET")return reply(PPO_TASK_WAYPOINT_IDS.map((id,index)=>({id,index})));
  if(url.pathname==="/api/robots"&&method==="GET")return reply({robots:[]});
  if(url.pathname==="/api/v1/task"&&method==="GET")return reply([...(v4?context:[]),...(task?[task]:[])]);
  if(url.pathname==="/api/v1/task"&&method==="POST"){
   const payload=route.request().postDataJSON();
   const expected={taskType:scenario.type,source:scenario.source,destination:scenario.destination,priority:scenario.priority,scheduledAt:scenario.createdSchedule};
   if(!Object.entries(expected).every(([k,v])=>payload[k]===v)){failure={payload,expected};return route.fulfill({status:422,json:{detail:"Demo payload mismatch"}});}
   events.push({event:"create-request",payload});
   await new Promise(resolve=>{createReply=resolve;});
   task={...payload,id:scenario.id,taskCode:scenario.code,status:"pending",createdAt:scenario.now,assignedRobot:null};
   events.push({event:"create-success",id:task.id});
   return reply(task);
  }
  if(url.pathname===`/api/v1/task/${scenario.id}/schedule`&&method==="PATCH"){
   const {scheduledAt}=route.request().postDataJSON();
   if(!task||scheduledAt!==scenario.revisedSchedule){failure={scheduledAt};return route.fulfill({status:422,json:{detail:"Demo reschedule mismatch"}});}
   task={...task,scheduledAt};
   events.push({event:"schedule-success",id:task.id,scheduledAt});
   return reply(task);
  }
  if(url.origin!==origin||method!=="GET"||url.pathname.startsWith("/api/"))return route.abort();
  if(url.pathname.endsWith("/DispatchMapScene.vue")&&!url.searchParams.has("vue")){
   const response=await route.fetch();
   const script=await response.text();
   const code=script.replace("renderer.render(scene, camera) }", "if(!window.filmFreeze) renderer.render(scene, camera) }")
     .replace("    frame = requestAnimationFrame(animate)\n", "    window.filmDraw=show=>{overlay.visible=show;controls.update();projectMarkers();renderer.render(scene,camera);};\n    frame = requestAnimationFrame(animate)\n");
   assert(code.includes("window.filmDraw"),"Capture hook did not match map");
   return route.fulfill({response,body:code});
  }
  return route.continue();
 });
 await page.routeWebSocket("**/*",socket=>socket.close());
 page.on("pageerror",error=>console.log("Page error",error.message));
 await page.goto(origin+"/?dispatchDebug=1",{waitUntil:"domcontentloaded"});
 await page.addStyleTag({content:"vite-plugin-vue-devtools,#vue-devtools__anchor{display:none!important}*,*::before,*::after{animation-duration:.001s!important;animation-delay:0s!important;transition-duration:.001s!important}"});
 await page.locator('[data-waypoint="ward_a_2"]').waitFor({timeout:120000});
 await page.locator('.dispatch-map .scene-message').waitFor({state:"hidden",timeout:30000});
 await page.evaluate(()=>{window.filmFreeze=true;window.filmDraw(false);});
 await page.locator(".dispatch-map-controls button").nth(1).click();
 await page.evaluate(()=>window.filmDraw(false));
 const cdp=await page.context().newCDPSession(page);
 let routeVisible=false;
 const editorialCaptures=new Set([
   "initial","type-options","source-fixed","map-clean","map-source","map-both","route","loading","confirm",
 ]);
 const shot=async(name)=>{
   if(hiDpi&&!editorialCaptures.has(name))return;
   const outputFile=new URL(name+".png",out);
   if(hiDpi&&process.argv.includes("--resume")){
     const previous=await readFile(outputFile).catch(()=>null);
     if(previous?.length>24&&previous.readUInt32BE(16)===3200&&previous.readUInt32BE(20)===1800) {
       console.log("Reusing",name);
       return;
     }
   }
   await page.evaluate(show=>window.filmDraw(show),routeVisible);
   if(v4) await page.waitForTimeout(180);
   if (hiDpi) {
     const {data}=await cdp.send("Page.captureScreenshot",{format:"png",fromSurface:true,clip:{x:0,y:0,width:1600,height:900,scale:2}});
     const bytes=Buffer.from(data,"base64");
     assert.equal(bytes.readUInt32BE(16),3200);
     assert.equal(bytes.readUInt32BE(20),1800);
     await writeFile(new URL(name+".png",out),bytes);
   } else {
     const {data}=await cdp.send("Page.captureScreenshot",{format:"png",fromSurface:true});
     await writeFile(new URL(name+".png",out),Buffer.from(data,"base64"));
   }
   console.log("Captured",name);
 };
 const points={};
 const mark=async(name,locator)=>{
   await locator.scrollIntoViewIfNeeded();
   const box=await locator.boundingBox();
   assert(box,name);
   points[name]={x:Math.round(box.x+box.width/2),y:Math.round(box.y+box.height/2),box};
 };
 const click=async(name,locator)=>{
   await mark(name,locator);
   await locator.click();
 };
 const type=page.locator(".task-type-trigger");
 const ward=page.locator('[data-waypoint="ward_a_2"]');
 const pharmacy=page.locator('[data-waypoint="pharmacy"]');
 const high=page.locator(".priority-control [data-priority=high]");
 const button=page.locator(".create-button");
 await page.locator("#dispatch-start-time").fill("14:20");
 await page.locator("#dispatch-start-time").blur();
 await type.click();
 await page.getByRole("option",{name:"Specimen delivery",exact:true}).click();
 await mark("type",type); await shot("initial");
 await type.click();
 const medicine=page.getByRole("option",{name:"Medication delivery",exact:true});
 await mark("medicine",medicine); await shot("type-options");
 if(!process.argv.includes("--entrance-only")){
 await medicine.click();
 assert(await page.getByRole("button",{name:"Source",exact:true}).isDisabled());
 await mark("pharmacy",pharmacy);
 await mark("ward",ward);
 await shot("source-fixed");
 if(v4){
   const hide=await page.addStyleTag({content:".is-source,.is-destination{visibility:hidden!important}"});
   await shot("map-clean");
   await hide.evaluate(el=>el.remove());
   const dest=await page.addStyleTag({content:".is-destination{visibility:hidden!important}"});
   await shot("map-source");
   await dest.evaluate(el=>el.remove());
 }
 if(v4) await ward.click(); else await ward.click({position:{x:10,y:28}});
 routeVisible=true;
 await page.locator('[data-waypoint="ward_a_2"].is-destination').waitFor();
 await page.waitForTimeout(350);
 await shot("route");
 if(v4){
   routeVisible=false;
   await shot("map-both");
   routeVisible=true;
 }
 await click("high",high);
 assert.equal(await high.getAttribute("aria-pressed"),"true");
 await mark("create",button); await shot("priority");
 await button.hover(); await page.mouse.down(); await page.mouse.up();
 for(let retry=0;!createReply&&retry<40;retry++)await new Promise(r=>setTimeout(r,50));
 assert(createReply,JSON.stringify(failure));
 assert(await button.isDisabled());
 assert.equal(await page.locator(".dispatch-toast.is-create-success").count(),0);
 await shot("loading");
 createReply();
 const toast=page.locator(".dispatch-toast.is-create-success");
 await toast.waitFor();
 assert((await toast.innerText()).includes(scenario.code));
 await mark("toast",toast);
 await mark("bell",page.locator(".notification-bell"));
 await shot("success");
 await page.locator(".notification-bell").hover();
 await page.locator("#notification-panel").getByText(new RegExp(scenario.code)).waitFor();
 await shot("notification");
 await page.mouse.move(950,680);
 // Close the toast via its original button if it is still visible.
 if(await toast.isVisible()) await toast.locator("button").click();
 await click("schedule",page.locator("#dispatch-schedule-tab"));
 const item=page.locator(".schedule-item").filter({hasText:scenario.code});
 await item.waitFor();
 assert((await item.locator("..").locator("..").innerText()).includes("14:20"));
 // Verify date navigation returns to the same task.
 await page.locator(".schedule-date-actions button").first().click();
 assert.equal(await item.count(),0);
 await page.locator(".schedule-date-navigation > button").first().click();
 await item.waitFor();
 await mark("task",item); await mark("edit",page.locator(".schedule-edit")); await shot("schedule");
 if(v4){
   const rows=page.locator(".schedule-slot");
   points.rows=await Promise.all((await rows.all()).map(row=>row.boundingBox()));
   points.taskCode=await item.locator(".schedule-card-top").boundingBox();
   assert.equal(await page.locator(".schedule-item").count(),6);
   if(v6) points.originalOrder=await page.locator(".schedule-card-top").allTextContents();
 }
 await page.locator(".schedule-edit").click();
 const input=item.locator(".schedule-time-entry input");
 await mark("time",input);
 if(v4) await input.focus();
 await shot("edit");
 await input.fill("15:05");
 const save=item.locator(".save-task-edits");
 await mark("save",save); await shot("new-time");
 await save.click();
 const confirm=page.locator(".confirm-reschedule");
 await mark("confirm",confirm); await shot("confirm");
 await confirm.click();
 await page.locator(".dispatch-toast.is-schedule-update").waitFor();
 assert.equal(task.scheduledAt,scenario.revisedSchedule,JSON.stringify(failure));
 assert((await item.locator("..").locator("..").innerText()).includes("15:05"));
 if(v4){
   await shot("saved-edit");
   await page.locator(".schedule-edit").click();
   assert.equal(await page.locator(".schedule-item").count(),6);
   if(v6){
     points.updatedOrder=await page.locator(".schedule-card-top").allTextContents();
     const pos=(rows,id)=>rows.findIndex(row=>row.includes(id));
     assert(pos(points.originalOrder,"T0002") < pos(points.originalOrder,"T0171"));
     assert(pos(points.updatedOrder,"T0002") > pos(points.updatedOrder,"T0171"));
   }
 }
 await shot("saved");
 await writeFile(new URL(hiDpi?"../src/task-creation-phase-vnext-capture.json":v6?"../src/task-creation-v6-capture.json":v4?"../src/task-creation-v4-capture.json":"../src/task-creation-capture.json",import.meta.url),JSON.stringify({points,events,task,...(v6?{context}:{}),viewport:{width:1600,height:900}},null,2)+"\n");
 console.log("Source locked; real Ward A marker, task POST, success, date navigation, edit and PATCH verified.");
 }
}finally{await browser.close();}
