import assert from "node:assert/strict";
import {createRequire} from "node:module";
import {mkdir,writeFile} from "node:fs/promises";
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.CAPTURE_PLAYWRIGHT||"playwright");
const frames = new URL("file:///tmp/medisync-v9-final/");
await mkdir(frames,{recursive:true});
const brake = require("remotion").Easing.bezier(.45,0,.06,1);
const origin="http://127.0.0.1:4185";
const output=new URL("../public/robot-status-phase-v9/",import.meta.url);
await mkdir(output,{recursive:true});
const ids=["C01","C02","M01","M02","W01","W02","W03"];
const robots=ids.map((id,i)=>({
  id:`robot-hospital_robot_${i+1}`,robotType:i<2?"clean":i<4?"medical":"ward",
  status:["執行任務中","待命","待命","執行任務中","充電中","充電中","充電中"][i],
  battery:[77,69,82,91,58,48,65][i],motorTemperature:[34,32,36,37,30,31,32][i],
  location:["Ward B","Waiting B","Ward A","Laboratory","Charging Station A","Charging Station A","Charging Station B"][i],
  levelName:"L1",hasTelemetry:true,lastUpdate:new Date().toISOString(),
}));
const records=[
  {taskCode:"T0004",status:"running",assignedRobot:robots[0].id},
  {taskCode:"T0002",status:"completed",assignedRobot:robots[2].id},
  {taskCode:"T0003",status:"running",assignedRobot:robots[3].id},
];
const browser=await chromium.launch({executablePath:process.env.CAPTURE_CHROMIUM,args:["--no-sandbox","--disable-gpu"]});
try {
  const context=await browser.newContext({viewport:{width:1600,height:820},timezoneId:"Asia/Taipei",locale:"en-US",deviceScaleFactor:1});
  const page=await context.newPage();
  await page.addInitScript(()=>localStorage.setItem("hospital-rmf-locale","en"));
  await page.routeWebSocket("**/*",socket=>socket.close());
  await page.route("**/*",async route=>{
    const req=route.request();
    const url=new URL(req.url());
    const cors={"access-control-allow-origin":origin,"access-control-allow-credentials":"true"};
    const reply=json=>route.fulfill({json,headers:cors});
    if(req.method()==="GET"){
      if(url.pathname==="/api/auth/me")return reply({id:"robot-status-film",name:"MediSync",email:"demo@example.invalid"});
      if(url.pathname==="/api/auth/csrf")return reply({token:"film-demo"});
      if(url.pathname==="/api/robots")return reply({robots:robots.map(robot=>({...robot,lastUpdate:new Date().toISOString()}))});
      if(url.pathname==="/api/v1/task")return reply(records);
    }
    if(url.origin!==origin||req.method()!=="GET"||url.pathname.startsWith("/api/"))return route.abort();
    if(url.pathname.endsWith("/RobotFleetView.vue")&&!url.searchParams.has("vue")){
      const response=await route.fetch();
      const source=await response.text();
      assert(source.includes("motorTemperature: null"));
      return route.fulfill({response,body:source.replace("motorTemperature: null","motorTemperature: entry.motorTemperature ?? null")});
    }
    if(url.pathname.endsWith("/useCountUp.js")){
      const response=await route.fetch();
      return route.fulfill({response,body:(await response.text()).replace("Math.max(0, Math.min((time - startedAt) / duration, 1))","window.__filmGaugeProgress ?? Math.max(0, Math.min((time - startedAt) / duration, 1))")});
    }
    if(url.pathname.endsWith("/RobotViewport.vue")&&!url.searchParams.has("vue")){
      const response=await route.fetch();
      const source=await response.text();
      assert(source.includes("onMounted(start)"));
      const body=source.replace("onMounted(start)","onMounted(() => { loading.value = false; emit('ready', { structureAvailable: true }) })")
        .replace("function resetView() {","function resetView() { if (!assembly) return");
      return route.fulfill({response,body});
    }
    return route.continue();
  });
  const errors = [];
  page.on("pageerror",error=>errors.push(error.message));
  await page.goto(origin+"/",{waitUntil:"domcontentloaded"});
  await page.addStyleTag({content:"vite-plugin-vue-devtools,#vue-devtools__anchor,#vue-devtools__container,[data-vue-devtools]{display:none!important} .battery-liquid{transition:none!important}"});
  await page.getByRole("button",{name:"Robot Status",exact:true}).click();
  await page.locator(".robot-hmi.stage-ready .robot-viewport").waitFor({timeout:30000});
  await page.evaluate(()=>document.fonts.ready);
  const list=page.locator(".robot-picker");
  const options=page.getByRole("option");
  assert.equal(await options.count(),7);
  const cdp=await context.newCDPSession(page);
  const option = id => options.filter({hasText:id});
  await option("C02").click();
  await page.mouse.move(650,95);
  await page.waitForTimeout(650);
  const box = await list.boundingBox();
  const targets = await Promise.all(["C01","M01"].map(id=>option(id).boundingBox()));
  const maxScroll = await list.evaluate(el=>el.scrollHeight-el.clientHeight);
  assert(maxScroll>=60,maxScroll);
  const navbar = await page.evaluate(() => {
    const node = [...document.querySelectorAll('button,a')].find(e=>e.textContent.trim()==='Robot Status');
    if (!node) throw Error('Robot Status navigation missing');
    const map = [...document.querySelectorAll('button,a')].find(e=>e.textContent.trim()==='Live Map');
    const rect = e => {const {x,y,width,height}=e.getBoundingClientRect();return {x,y,width,height};};
    return {status:rect(node),map:rect(map),activeClass:node.className,navBottom:node.closest('header')?.getBoundingClientRect().bottom || rect(node).y+rect(node).height+12};
  });
  console.log({box,targets,maxScroll,navbar});
  await writeFile(new URL("../../src/robot-status-phase-v9-capture.json",output),JSON.stringify({box,targets,maxScroll,navbar},null,2));
  const image = async (format,quality) => Buffer.from((await cdp.send("Page.captureScreenshot",{format,quality,fromSurface:true,optimizeForSpeed:true,clip:{x:0,y:0,width:1600,height:820,scale:1.2}})).data,"base64");
  await writeFile(new URL("native-page.png",output),await image("png"));
  const setNav = active => page.evaluate(active => {
    for (const node of document.querySelectorAll(".overview-nav__link")) {
      if (["Live Map","Robot Status"].includes(node.textContent.trim())) {
        node.classList.toggle("overview-nav__link--active",node.textContent.trim() === active);
      }
    }
  },active);
  await setNav("Live Map");
  await writeFile(new URL("map-navbar.png",output),await image("png"));
  if (!process.argv.includes("--navbar-only")) {
  await setNav("Robot Status");
  let previous;
  for(let f=0;f<195;f++){
    const start = f < 133 ? 65 : 133;
    await page.evaluate(progress=>window.__filmGaugeProgress=progress,Math.min(1,Math.max(0,(f-start)/12)));
    if(f===65 || f===133){
      const target = await option(f===65?"C01":"M01").boundingBox();
      await page.mouse.click(target.x+target.width*.5,target.y+target.height*.52);
    }
    const scroll=maxScroll*brake(Math.min(1,Math.max(0,(f-83)/35)));
    const hover=f>=54&&f<65?"C01":f>=125&&f<133?"M01":null;
    if(f===54||f===125){
      const at=targets[hover==="C01"?0:1];
      await page.mouse.move(at.x+at.width*.5,at.y+at.height*.52-scroll);
    }
    if(f===65||f===133)await page.mouse.move(650,95);
    await list.evaluate((el,top)=>el.scrollTop=top,scroll);
    if((f>=65&&f<=77)||(f>=133&&f<=145)) {
      await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
    }
    if(f===65||f===133)assert.equal(await option(f===65?"C01":"M01").getAttribute("aria-selected"),"true");
    if(!previous||[54,125].includes(f)||(f>=65&&f<=77)||(f>=84&&f<=118)||(f>=133&&f<=145)) previous=await image("jpeg",99);
    await writeFile(new URL(String(f).padStart(3,"0")+".jpg",frames),previous);
    if ([0,77,145].includes(f)) {
      const expected = f===0 ? ["C02",69,32] : f===77 ? ["C01",77,34] : ["M01",82,36];
      const readout = await page.evaluate(()=>[
        document.querySelector(".robot-info-card__facts dd").textContent.trim(),
        parseInt(document.querySelector(".battery-reading").textContent),
        parseInt(document.querySelector(".thermal-reading").textContent),
      ]);
      assert.deepEqual(readout,expected);
    }
    if(f%30===0)console.log("Vue frame",f);
  }
  }
  assert.deepEqual(errors,[]);
} finally { await browser.close(); }
