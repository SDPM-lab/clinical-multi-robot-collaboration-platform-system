import assert from "node:assert/strict";
import {createRequire} from "node:module";
import {access,mkdir,writeFile} from "node:fs/promises";
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.CAPTURE_PLAYWRIGHT||"playwright");
const origin="http://127.0.0.1:4179";
const output=new URL("../public/robot-status-phase-v2/",import.meta.url);
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
  const context=await browser.newContext({viewport:{width:1600,height:820},timezoneId:"Asia/Taipei",locale:"en-US",reducedMotion:"reduce"});
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
    const {data}=await cdp.send("Page.captureScreenshot",{format:"png",fromSurface:true,clip:{x:0,y:0,width:1600,height:820,scale:1.5}});
    const png=Buffer.from(data,"base64");
    assert.equal(png.readUInt32BE(16),2400);
    assert.equal(png.readUInt32BE(20),1230);
    await writeFile(new URL(name+".png",output),png);
    console.log(name,png.length);
  };
  await page.waitForTimeout(1100);
  const geometry=await page.evaluate(()=>{
    const box=selector=>{
      const {x,y,width,height}=document.querySelector(selector).getBoundingClientRect();
      return {x,y,width,height};
    };
    const node=document.querySelector(".robot-picker");
    return {list:box(".robot-picker"),viewport:box(".robot-viewport"),metrics:box(".robot-side-metrics"),
      information:box(".robot-info-card"),row:box(".robot-list-item"),maxScroll:node.scrollHeight-node.clientHeight};
  });
  await shot("c01");
  await list.evaluate(node=>node.scrollTop=node.scrollHeight);
  await shot("c01-scroll");
  await list.evaluate(node=>node.scrollTop=0);
  await options.filter({hasText:"M01"}).click();
  assert.equal(await options.filter({hasText:"M01"}).getAttribute("aria-selected"),"true");
  await page.mouse.move(800,80);
  await page.waitForTimeout(1100);
  await shot("m01");
  const nativeTarget=page.getByRole("option").filter({hasText:"M01"});
  geometry.m01=await nativeTarget.boundingBox();
  geometry.controls={};
  for(const [label,name] of [["Head","head"],["Left arm","arm"],["Whole robot","whole"]]){
    const control=page.getByRole("button",{name:label,exact:true});
    geometry.controls[name]=await control.boundingBox();
    assert(geometry.controls[name],label);
    if(name==="whole")break;
    await control.click();
    assert.equal(await control.getAttribute("aria-pressed"),"true");
    await page.mouse.move(800,80);
    await page.waitForTimeout(850);
    await shot(name);
  }
  await writeFile(new URL("../src/robot-status-phase-v2-capture.json",import.meta.url),JSON.stringify(geometry,null,2)+"\n");
  console.log(geometry);
}finally{await browser.close();}
