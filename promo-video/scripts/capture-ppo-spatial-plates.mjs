import {chromium} from "/tmp/medisync-capture/node_modules/playwright/index.mjs";
import fs from "node:fs";
const sections=[[0,58,89],[90,148,179],[180,231,299],[300,368,389],[390,433,449]];
const browser=await chromium.launch({executablePath:"/tmp/chromium",args:["--no-sandbox","--use-gl=angle","--use-angle=swiftshader","--enable-unsafe-swiftshader"]});
try {
 const page=await browser.newPage();
 page.on("pageerror",e=>console.error(e.message));
 await page.goto("http://127.0.0.1:4188/.ppo-canvas-capture.html");
 await page.waitForFunction(()=>typeof window.takeFrame==="function",{},{timeout:100000});
 const frames={};
 for(const [start,stop] of sections){
   const interval=start===90?12:6;
   const section=[...new Set([...Array.from({length:Math.floor((stop-start)/interval)+1},(_,i)=>start+i*interval),stop,...(start===90?[134,135]:[])])].sort((a,b)=>a-b);
   for(const f of section){
     const {image,points}=await page.evaluate(f=>window.takeFrame(f),f);
     fs.writeFileSync(`/tmp/medisync-ppo-plates/${f}.png`,Buffer.from(image,"base64"));
     frames[f]=points;
   }
   console.log("Captured 3D section",start,stop);
   fs.writeFileSync("/tmp/medisync-ppo-plates/points.json",JSON.stringify(frames));
 }
}finally{await browser.close()}
