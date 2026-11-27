import assert from "node:assert/strict";
import {createRequire} from "node:module";
import {mkdir,writeFile} from "node:fs/promises";
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.CAPTURE_PLAYWRIGHT||"playwright");
const frames = new URL("file:///tmp/medisync-v10-final-capture/");
await mkdir(frames,{recursive:true});
const brake = require("remotion").Easing.bezier(.45,0,.06,1);
const origin="http://127.0.0.1:4185";
const output=new URL("../public/robot-status-phase-v10/",import.meta.url);
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
  const distance=24;
  assert(distance<=maxScroll);
  const timing={scrollStart:58,scrollEnd:91,c01:103,m01:129,c01Telemetry:18,m01Telemetry:44,frames:195};
  await writeFile(new URL("../../src/robot-status-phase-v10-capture.json",output),JSON.stringify({targets,distance,timing},null,2));
  const image=async () => {
    const {data}=await cdp.send("Page.captureScreenshot",{
      format:"jpeg",quality:98,optimizeForSpeed:true,fromSurface:true,
      clip:{x:0,y:0,width:1600,height:820,scale:2},
    });
    return Buffer.from(data,"base64");
  };
  const verify=async expected=>{
    const readout=await page.evaluate(()=>[
      document.querySelector(".robot-info-card__facts dd").textContent.trim(),
      parseInt(document.querySelector(".battery-reading").textContent),
      parseInt(document.querySelector(".thermal-reading").textContent),
    ]);
    assert.deepEqual(readout,expected);
  };
  const moveTo=async id=>{
    const target=await option(id).boundingBox();
    const x=target.x+target.width*.5, y=target.y+target.height*.60;
    assert(y>box.y && y<box.y+box.height);
    await page.mouse.move(x,y);
    return [x,y];
  };

  // Use the actual Vue scroll container and native hover/selection events.
  let previous;
  let previousScroll=-1;
  for(let f=0;f<timing.frames;f++){
    const click=f===timing.c01 ? "C01" : f===timing.m01 ? "M01" : null;
    const start=f<timing.m01 ? timing.c01 : timing.m01;
    const gaugeLength=start===timing.c01 ? timing.c01Telemetry : timing.m01Telemetry;
    const gauge=f>=start && f<=start+gaugeLength;
    const scroll=distance*brake(Math.max(0,Math.min(1,(f-timing.scrollStart)/(timing.scrollEnd-timing.scrollStart))));
    const scrollChanged=scroll!==previousScroll;
    if(scrollChanged)await list.evaluate((el,top)=>{
      const rounded=Math.round(top);
      el.scrollTop=rounded;
      // scrollTop is integer in Chromium. Preserve the fractional camera-frame position.
      for(const row of el.querySelectorAll(".robot-list-entry")){
        row.style.translate=`0 ${rounded-top}px`;
      }
    },scroll);
    if(gauge){
      const t=(f-start)/gaugeLength;
      // Keep the M01 interpolation readable as the right side comes into view.
      await page.evaluate(t=>window.__filmGaugeProgress=t,start===timing.m01?t**3:t);
    }
    if(f===98)await moveTo("C01");
    if(f===123)await moveTo("M01");
    if(click){
      const [x,y]=await moveTo(click);
      await page.mouse.click(x,y);
      assert.equal(await option(click).getAttribute("aria-selected"),"true");
    }
    if(gauge || scrollChanged || f===98 || f===123){
      await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
      previous=await image();
    }
    await writeFile(new URL(String(f).padStart(3,"0")+".jpg",frames),previous);
    previousScroll=scroll;
    if(f===0)await verify(["C02",69,32]);
    if(f===timing.c01+timing.c01Telemetry)await verify(["C01",77,34]);
    if(f===timing.m01+timing.m01Telemetry)await verify(["M01",82,36]);
    if(f%30===0)console.log("Vue frame",f);
  }
  assert.deepEqual(errors,[]);
} finally {
  await browser.close();
}
