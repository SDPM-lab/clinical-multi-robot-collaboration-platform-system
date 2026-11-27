import {createRequire} from "node:module";
import {readFile,writeFile} from "node:fs/promises";
import {resolve} from "node:path";
import {TASK_LOCATION_IDS} from "../../frontend/src/config/taskTypes.js";
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.CAPTURE_DEPENDENCIES
  ? resolve(process.env.CAPTURE_DEPENDENCIES,"node_modules/playwright") : "playwright");
const v5=process.argv.includes("--v5");
const version=v5?"dashboard-v5":"dashboard-v4";
const demo=JSON.parse(await readFile(new URL(`../src/${version}-demo.json`,import.meta.url),"utf8"));
const output=new URL(`../public/${version}/`,import.meta.url);
const origin="http://127.0.0.1:4179";
const stamp="2026-11-20T11:10:00+08:00";
const ids=Object.fromEntries(demo.robots.map((r,i)=>[r.code,i<7?`robot-hospital_robot_${i+1}`:r.code]));
const routes=demo.tasks.map(t=>{
 const location=TASK_LOCATION_IDS[t.type];
 return {id:t.id,taskCode:t.id,taskType:t.type,status:t.status,dispatched:t.status!=="pending",
  assignedRobot:ids[t.robot]||null,source:t.type==="specimen_delivery"?"blood_draw":location.sources[0],
  destination:location.destinations[0],scheduledAt:`2026-11-20T${t.time}:00+08:00`};
});
const snapshot={robots:demo.robots.map(r=>({id:ids[r.code],levelName:`L${r.floor}`,
 hasTelemetry:r.connected!==false,battery:r.history.at(-1).battery,lastUpdate:stamp,
 status:r.connected===false?"離線":demo.tasks.some(t=>t.robot===r.code&&t.status==="running")?"執行任務中":"待命",
 location:r.code===demo.selected.robot?"Blood Draw":"Ward A"}))};
const chartRobots=[...demo.robots,...(demo.chartExtras ?? [])];
const history=Object.fromEntries([1,2,3].map(floor=>[`floor${floor}`,demo.robots[0].history.map((point,i)=>({
 time:point.time,batteries:Object.fromEntries(chartRobots.filter(r=>r.floor===floor).map(r=>[r.code,r.history[i].battery])),
}))]));
const wide=process.argv.includes("--wide");
const chartOnly=!wide;
const browser=await chromium.launch({executablePath:process.env.CAPTURE_CHROMIUM,
 args:chartOnly ? ["--no-sandbox","--disable-webgl"] : ["--no-sandbox","--use-gl=angle","--use-angle=swiftshader","--enable-unsafe-swiftshader"]});
try{
 const page=await browser.newPage({viewport:{width:1600,height:900},locale:"en-US",timezoneId:"Asia/Taipei",reducedMotion:"reduce"});
 await page.addInitScript(()=>{
   localStorage.setItem("hospital-rmf-locale","en");
   const wide = location.search.includes("filmWide=1");
   if (wide) {
     const target = {x:-1.0448,y:5.883,z:2.8285};
     const position = {x:17.3507,y:9.1058,z:29.7501};
     const distance=1.67;
     const lift=0.45;
     localStorage.setItem("overview-camera-preset-v9",JSON.stringify({
       position:{x:target.x+(position.x-target.x)*distance,y:target.y+(position.y-target.y)*distance+lift,z:target.z+(position.z-target.z)*distance},
       target:{...target,y:target.y+lift},
     }));
   }
   const raf=requestAnimationFrame.bind(window);
   window.requestAnimationFrame=callback=>raf(time=>{if(!window.freezeFilm)callback(time);});
 });
 await page.clock.setFixedTime(new Date(stamp));
 let paused=false;
 await page.route("**/*",async route=>{
  const url=new URL(route.request().url());
  if(route.request().method()!=="GET")return route.abort();
  if(url.pathname==="/api/auth/me")return route.fulfill({json:{id:"film-demo",name:"MediSync Demo"}});
  if(url.pathname==="/api/robots")return paused ? undefined : route.fulfill({json:snapshot});
  if(url.pathname==="/api/v1/task")return route.fulfill({json:routes});
  if(url.origin!==origin||url.pathname.startsWith("/api/"))return route.abort();
  if(url.pathname.endsWith("/BuildingTrendPanel.vue")&&!url.searchParams.has("vue")){
   // Only the capture browser sees the expanded chart legend.
   const response=await route.fetch();
   const compiled=await response.text();
   const ids=JSON.stringify(chartRobots.map(robot=>robot.code));
   const extraColors=JSON.stringify(Object.fromEntries((v5 ? demo.robots.slice(7) : demo.chartExtras).map(robot=>[robot.code,robot.color])));
   const module=compiled
    .replace(/import \{ robotIds \} from "[^"]+"/, `const robotIds = ${ids}; const extraColors = ${extraColors};`)
    .replace('getRobotVisualTheme(id).main','extraColors[id] || getRobotVisualTheme(id).main')
    .replace('robotIndex-3','(robotIndex<7?robotIndex-3:robotIndex<10?robotIndex-8:robotIndex-12)');
   if(!module.includes('const extraColors'))throw Error("Chart fixture transform did not match the local component.");
   return route.fulfill({response,body:module});
  }
  return route.continue();
 });
 await page.routeWebSocket("**/*",socket=>socket.close());
 await page.goto(wide ? origin+"/?filmWide=1" : origin,{waitUntil:"domcontentloaded"});
 await page.addStyleTag({content:`
  vite-plugin-vue-devtools, #vue-devtools__anchor, .clinic-overview-scene .shared-loading-leave-active{display:none!important}
  .right-information-stack *, .overview-bottom-main * {animation:none!important;transition:none!important}
  .schedule-list li{opacity:1!important}
 `});
 await page.waitForFunction(skipModel=>{
   const loader=document.querySelector(".clinic-overview-scene .scene-message");
   return (skipModel || document.querySelector(".clinic-overview-scene canvas")&&(!loader||loader.classList.contains("shared-loading-leave-active")))
     &&document.querySelectorAll(".schedule-list li").length===24&&document.querySelector(".progress-content li");
 },chartOnly,{polling:300,timeout:120000});
 paused=true;
 const info=await page.evaluate(({history,tasks,robot})=>{
   const chart=document.querySelector(".building-trend-panel");
   const network=document.querySelector(".overview-connectivity > :first-child");
   const chartProps=chart.__vueParentComponent?.props;
   const networkProps=network.__vueParentComponent?.props;
   if(!chartProps||!networkProps)throw Error("Native Vue component capture hooks were not found.");
   chartProps.history=history;
   chartProps.source="Simulated";
   networkProps.status="online";
   const scroll=document.querySelector(".schedule-list");
   const rows=[...scroll.querySelectorAll("li")];
   const visibleStart=tasks.length-8;
   rows.forEach((row,i)=>{
     const color=tasks[i]?.color;
     if(color) row.querySelector("i").style.background=color;
   });
   scroll.scrollTop=rows[visibleStart].offsetTop-rows[0].offsetTop;
   const timeline=document.querySelector(".task-progress-panel").__vueParentComponent;
   timeline?.emit("update:modelValue",robot);
   return {chart:!!chartProps.history.floor3,network:networkProps.status};
 },{history,tasks:[...demo.tasks].sort((a,b)=>a.time.localeCompare(b.time)),robot:ids[demo.selected.robot]});
 await page.waitForFunction(expected=>document.querySelectorAll(".robot-bar").length===expected && [...document.querySelectorAll(".connectivity-panel")].some(n=>n.dataset.state==="online"),chartRobots.reduce((count,robot)=>count+robot.history.length,0),{polling:300,timeout:30000});
 console.log("Native panels populated",info);
 if(wide){
  await page.addStyleTag({content:`.completion-panel,.overview-calendar,.task-progress-panel,.overview-connectivity,.overview-bottom-main{visibility:hidden!important} :root{--animation-duration:0s}`});
  await page.evaluate(()=>{window.freezeFilm=true;});
  const cdp=await page.context().newCDPSession(page);
  const {data}=await cdp.send("Page.captureScreenshot",{format:"png",fromSurface:true});
  await writeFile(new URL("wide-capture.png",output),Buffer.from(data,"base64"));
  console.log("Captured isolated wide WebGL clinic.");
 }else{
 if(v5){
  const net=page.locator(".overview-connectivity > :first-child");
  const fleet=page.locator(".overview-connectivity > :last-child");
  const scene=await page.evaluate(()=>{
   const bounds=(element,parent)=>{const b=element.getBoundingClientRect(),a=parent.getBoundingClientRect();return {x:b.x-a.x,y:b.y-a.y,w:b.width,h:b.height};};
   const net=document.querySelector(".overview-connectivity > :first-child");
   const svg=net.querySelector("svg");
   const fleet=document.querySelector(".overview-connectivity > :last-child");
   return {wifi:bounds(svg,net),orange:getComputedStyle(svg).color,fleet:{count:bounds(fleet.querySelector(".connection-count"),fleet),caption:bounds(fleet.querySelector("p"),fleet)}};
  });
  await page.addStyleTag({content:".overview-connectivity .network-signal,.overview-connectivity .connection-count,.overview-connectivity > :last-child p{visibility:hidden!important}"});
  await net.screenshot({path:new URL("network-empty.png",output).pathname});
  await fleet.screenshot({path:new URL("fleet-empty.png",output).pathname});
  await writeFile(new URL("../src/dashboard-v5-metrics.json",import.meta.url),JSON.stringify(scene,null,2)+"\n");
 }
 const chart=page.locator(".overview-bottom-main");
 const metadata=await chart.evaluate(node=>{
  const panel=node.getBoundingClientRect();
  const bounds=el=>{const r=el.getBoundingClientRect();return {x:r.x-panel.x,y:r.y-panel.y,w:r.width,h:r.height};};
  return {bars:[...node.querySelectorAll(".robot-bar")].map(el=>({...bounds(el),floor:[...node.querySelectorAll(".floor-chart")].indexOf(el.closest(".floor-chart"))})),legend:[...node.querySelectorAll(".chart-legend span")].map(bounds)};
 });
 const gauge=page.locator(".completion-panel");
 const {dial,completion,fleet}=await page.evaluate(()=>{
  const measure=(element,parent)=>{const b=element.getBoundingClientRect(),a=parent.getBoundingClientRect();return {x:b.x-a.x,y:b.y-a.y,w:b.width,h:b.height};};
  const gauge=document.querySelector(".completion-panel");
  const dial=gauge.querySelector("svg");
  const fleet=document.querySelector(".overview-connectivity > :last-child");
  return {dial:measure(dial,gauge),completion:{ink:getComputedStyle(dial.querySelector(".speed-number")).fill,needle:getComputedStyle(dial.querySelector(".speed-needle")).fill},fleet:{number:measure(fleet.querySelector(".connection-count strong"),fleet),caption:measure(fleet.querySelector("p"),fleet)}};
 });
 await page.addStyleTag({content:".speed-needle,.speed-arc,.speed-number{visibility:hidden!important}.completion-panel,.completion-panel *{animation:none!important;transition:none!important}"});
 await gauge.screenshot({path:new URL("gauge-empty.png",output).pathname});
 await writeFile(new URL(`../src/${version}-gauge.json`,import.meta.url),JSON.stringify({dial,completion,fleet},null,2)+"\n");
 await chart.screenshot({path:new URL("battery.png",output).pathname});
 await page.addStyleTag({content:".robot-bar{visibility:hidden!important}"});
 await chart.screenshot({path:new URL("battery-empty.png",output).pathname});
 await writeFile(new URL(`../src/${version}-chart.json`,import.meta.url),JSON.stringify(metadata,null,2)+"\n");
 console.log("Captured native chart, empty chart and measured bar and legend bounds.");
 }
}finally{await browser.close();}
