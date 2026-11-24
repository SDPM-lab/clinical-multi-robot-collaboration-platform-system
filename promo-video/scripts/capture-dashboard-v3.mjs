import {createRequire} from "node:module";
import {readFile,writeFile} from "node:fs/promises";
import {resolve} from "node:path";
import {TASK_LOCATION_IDS} from "../../frontend/src/config/taskTypes.js";
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.CAPTURE_DEPENDENCIES
  ? resolve(process.env.CAPTURE_DEPENDENCIES,"node_modules/playwright") : "playwright");
const demo=JSON.parse(await readFile(new URL("../src/dashboard-v3-demo.json",import.meta.url),"utf8"));
const output=new URL("../public/dashboard-v3/",import.meta.url);
const origin="http://127.0.0.1:4179";
const stamp="2026-11-20T11:10:00+08:00";
const ids=Object.fromEntries(demo.robots.map((r,i)=>[r.code,`robot-hospital_robot_${i+1}`]));
const routes=demo.tasks.map(t=>{
 const location=TASK_LOCATION_IDS[t.type];
 return {id:t.id,taskCode:t.id,taskType:t.type,status:t.status,dispatched:t.status!=="pending",
  assignedRobot:ids[t.robot]||null,source:t.type==="specimen_delivery"?"blood_draw":location.sources[0],
  destination:location.destinations[0],scheduledAt:`2026-11-20T${t.time}:00+08:00`};
});
const snapshot={robots:demo.robots.map(r=>({id:ids[r.code],levelName:`L${r.floor}`,
 hasTelemetry:true,battery:r.history.at(-1).battery,lastUpdate:stamp,
 status:demo.tasks.some(t=>t.robot===r.code&&t.status==="running")?"執行任務中":"待命",
 location:r.code===demo.selected.robot?"Blood Draw":"Ward A"}))};
const history=Object.fromEntries([1,2,3].map(floor=>[`floor${floor}`,demo.robots[0].history.map((point,i)=>({
 time:point.time,batteries:Object.fromEntries(demo.robots.filter(r=>r.floor===floor).map(r=>[r.code,r.history[i].battery])),
}))]));
const chartOnly=process.argv.includes("--chart-only");
const browser=await chromium.launch({executablePath:process.env.CAPTURE_CHROMIUM,
 args:chartOnly ? ["--no-sandbox","--disable-webgl"] : ["--no-sandbox","--use-gl=angle","--use-angle=swiftshader","--enable-unsafe-swiftshader"]});
try{
 const page=await browser.newPage({viewport:{width:1600,height:900},locale:"en-US",timezoneId:"Asia/Taipei",reducedMotion:"reduce"});
 await page.addInitScript(()=>{
   localStorage.setItem("hospital-rmf-locale","en");
   const raf=requestAnimationFrame.bind(window);
   window.requestAnimationFrame=callback=>raf(time=>{if(!window.freezeFilm)callback(time);});
 });
 await page.clock.setFixedTime(new Date(stamp));
 let paused=false;
 await page.route("**/*",route=>{
  const url=new URL(route.request().url());
  if(route.request().method()!=="GET")return route.abort();
  if(url.pathname==="/api/auth/me")return route.fulfill({json:{id:"film-demo",name:"MediSync Demo"}});
  if(url.pathname==="/api/robots")return paused ? undefined : route.fulfill({json:snapshot});
  if(url.pathname==="/api/v1/task")return route.fulfill({json:routes});
  if(url.origin!==origin||url.pathname.startsWith("/api/"))return route.abort();
  return route.continue();
 });
 await page.routeWebSocket("**/*",socket=>socket.close());
 await page.goto(origin,{waitUntil:"domcontentloaded"});
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
 await page.waitForFunction(()=>document.querySelectorAll(".robot-bar").length===28 && [...document.querySelectorAll(".connectivity-panel")].some(n=>n.dataset.state==="online"),undefined,{polling:300,timeout:30000});
 console.log("Native panels populated",info);
 const boxes=await page.evaluate(()=>{
  const selectors={gauge:".completion-panel",schedule:".overview-calendar",progress:".task-progress-panel",
   network:".overview-connectivity > :first-child",fleet:".overview-connectivity > :last-child",battery:".overview-bottom-main"};
  return Object.fromEntries(Object.entries(selectors).map(([key,selector])=>{
    const r=document.querySelector(selector).getBoundingClientRect();
    return [key,{x:Math.round(r.x),y:Math.round(r.y),width:Math.round(r.width),height:Math.round(r.height),selector}];
  }));
 });
 await writeFile(new URL("native-layout.json",output),JSON.stringify(boxes,null,2)+"\n");
 if(chartOnly){
   await page.locator(".overview-bottom-main").screenshot({path:new URL("native-chart-supplement.png",output).pathname});
   console.log("Native chart capture completed.");
 }else{
 await page.evaluate(()=>{window.freezeFilm=true;});
 const cdp=await page.context().newCDPSession(page);
 const shot=async name=>{
  const {data}=await cdp.send("Page.captureScreenshot",{format:"png",fromSurface:true});
  await writeFile(new URL(name+".png",output),Buffer.from(data,"base64"));
 };
 await shot("native-overview");
 console.log("Overview image captured");
 await page.addStyleTag({content:Object.values(boxes).map(p=>p.selector).join(",")+"{visibility:hidden!important}"});
 await shot("native-base");
 console.log("Native capture completed.");
 }
}finally{await browser.close();}
