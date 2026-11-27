import assert from "node:assert/strict";
import {createRequire} from "node:module";
import {access,mkdir,writeFile} from "node:fs/promises";
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.CAPTURE_PLAYWRIGHT||"playwright");
const completeOnly=process.argv.includes("--complete-only");
const origin="http://127.0.0.1:4185";
const output=new URL("../public/robot-status-phase-v5/",import.meta.url);
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
const browser=await chromium.launch({executablePath:process.env.CAPTURE_CHROMIUM,args:["--no-sandbox","--use-gl=angle","--use-angle=swiftshader","--enable-unsafe-swiftshader"]});
try {
  const context=await browser.newContext({viewport:{width:1600,height:completeOnly?930:820},timezoneId:"Asia/Taipei",locale:"en-US",reducedMotion:"reduce"});
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
    if(url.pathname.endsWith("/RobotViewport.vue")&&!url.searchParams.has("vue")){
      const response=await route.fetch();
      const body=(await response.text()).replace("alpha: true, antialias: true","alpha: true, antialias: true, preserveDrawingBuffer: true")
        .replace("if (document.hidden || !assembly) return","if (document.hidden || !assembly || window.__filmPause) return");
      assert(body.includes("window.__filmPause"));
      return route.fulfill({response,body});
    }
    return route.continue();
  });
  page.on("pageerror",error=>console.log(error.message));
  await page.goto(origin+"/?robotDebug=1",{waitUntil:"domcontentloaded"});
  await page.addStyleTag({content:"vite-plugin-vue-devtools,#vue-devtools__anchor,#vue-devtools__container,[data-vue-devtools]{display:none!important}"});
  await page.locator(".robot-hmi.stage-ready .robot-viewport canvas").waitFor({timeout:120000});
  await page.evaluate(()=>document.fonts.ready);
  const list=page.locator(".robot-picker");
  const options=page.getByRole("option");
  assert.equal(await options.count(),7);
  const cdp=await context.newCDPSession(page);
  const shot=async name=>{
    const target=new URL(name+".png",output);
    if(process.argv.includes("--resume")&&await access(target).then(()=>true,()=>false))return;
    const {data}=await cdp.send("Page.captureScreenshot",{format:"png",fromSurface:true,clip:{x:0,y:0,width:1600,height:page.viewportSize().height,scale:1.5}});
    const png=Buffer.from(data,"base64");
    assert.equal(png.readUInt32BE(16),2400);
    assert.equal(png.readUInt32BE(20),page.viewportSize().height*1.5);
    await writeFile(new URL(name+".png",output),png);
    console.log(name,png.length);
  };
  await options.filter({hasText:"M01"}).click();
  assert.equal(await options.filter({hasText:"M01"}).getAttribute("aria-selected"),"true");
  await page.mouse.move(801,80);
  const canvas=page.locator(".robot-viewport canvas");
  await page.waitForTimeout(1000);
  if(!completeOnly){
    await canvas.evaluate(el=>el.style.visibility="hidden");
    await shot("m01-viewport-clean");
    await canvas.evaluate(el=>el.style.visibility="visible");
    await page.setViewportSize({width:1600,height:930});
    await page.waitForTimeout(1000);
  }
  await page.evaluate(()=>window.__filmPause=true);
  const visible=await list.evaluate(el=>{
    const box=el.getBoundingClientRect();
    return Array.from(el.querySelectorAll("[role=option]")).filter(row=>{
      const r=row.getBoundingClientRect();
      return r.top>=box.top&&r.bottom<=box.bottom;
    }).length;
  });
  assert.equal(visible,7);
  await shot("m01-complete");
}finally{await browser.close();}
