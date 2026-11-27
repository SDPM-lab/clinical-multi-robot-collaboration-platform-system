import assert from "node:assert/strict";
import {createRequire} from "node:module";
import {mkdir,writeFile} from "node:fs/promises";
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.CAPTURE_PLAYWRIGHT||"playwright");
const frames = new URL("file:///tmp/medisync-v12-fleet/");
await mkdir(frames,{recursive:true});
const brake = require("remotion").Easing.bezier(.45,0,.06,1);
const origin="http://127.0.0.1:4185";
const output=new URL("../public/robot-status-phase-v12/",import.meta.url);
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
  const context=await browser.newContext({viewport:{width:1600,height:650},timezoneId:"Asia/Taipei",locale:"en-US",deviceScaleFactor:1});
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
  const clip={x:20,y:80,width:348,height:570,scale:2};
  const maxScroll=await list.evaluate(el=>el.scrollHeight-el.clientHeight);
  assert(maxScroll>=100,maxScroll);
  const timing={duration:126,scrollStart:13,scrollEnd:63,selectW02:77,returnStart:83,returnEnd:103,selectM01:115};
  const targets={};
  const seen=new Set();
  const ratio=(f,a,b)=>Math.min(1,Math.max(0,(f-a)/(b-a)));
  const ease=require("remotion").Easing.bezier(.29,0,.24,1);
  const sample=async ()=>{
    const {data}=await cdp.send("Page.captureScreenshot",{
      format:"jpeg",quality:97,optimizeForSpeed:true,fromSurface:true,clip,
    });
    return Buffer.from(data,"base64");
  };
  let previous,prevScroll;
  for(let frame=0;frame<timing.duration;frame++){
    const scroll=maxScroll*brake(ratio(frame,timing.scrollStart,timing.scrollEnd))
      -(maxScroll-104)*ease(ratio(frame,timing.returnStart,timing.returnEnd));
    const changed=scroll!==prevScroll;
    if(changed){
      const visible=await list.evaluate((el,top)=>{
        const rounded=Math.round(top);
        el.scrollTop=rounded;
        const bounds=el.getBoundingClientRect();
        return [...el.querySelectorAll(".robot-list-entry")].flatMap(row=>{
          row.style.translate=`0 ${rounded-top}px`;
          const r=row.getBoundingClientRect();
          return Math.min(r.bottom,bounds.bottom)-Math.max(r.top,bounds.top)>r.height*.61
            ? [row.textContent.match(/(?:C|M|W)0[123]/)?.[0]]
            : [];
        });
      },scroll);
      for(const id of visible) if(id)seen.add(id);
    }
    const robot=frame===timing.selectW02-7||frame===timing.selectW02?"W02"
      :frame===timing.selectM01-7||frame===timing.selectM01?"M01":null;
    if(robot){
      const target=await option(robot).boundingBox();
      const x=target.x+target.width*.54, y=target.y+target.height*.49;
      assert(y>box.y && y<box.y+box.height,[robot,y,box]);
      await page.mouse.move(x,y);
      targets[robot]=[(x-clip.x)*2,(y-clip.y)*2];
      if(frame===timing.selectW02||frame===timing.selectM01){
        await page.mouse.click(x,y);
        assert.equal(await option(robot).getAttribute("aria-selected"),"true");
      }
    }
    if(changed||robot){
      await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
      previous=await sample();
    }
    await writeFile(new URL(String(frame).padStart(3,"0")+".jpg",frames),previous);
    prevScroll=scroll;
    if(frame%30===0)console.log("Fleet",frame);
  }
  assert.deepEqual([...seen].sort(),[...ids].sort());
  assert.deepEqual(errors,[]);
  console.log({seen:[...seen],maxScroll,targets});
  await writeFile(new URL("../../src/robot-status-phase-v12-capture.json",output),JSON.stringify({timing,targets,width:clip.width*2,height:clip.height*2,maxScroll},null,2));
} finally {
  await browser.close();
}
