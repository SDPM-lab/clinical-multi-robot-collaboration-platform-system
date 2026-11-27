import {AbsoluteFill, Audio, Easing, Img, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame} from "remotion";
import captions from "./live-map-tracking-v2-captions.json";
import capture from "./live-map-tracking-v2-capture.json";

const orange="#d94f1b";
const ink="#221e1c";
const muted="#675b53";
const paper="#fbf8f4";
const line="#e6d7cd";
const asset=(name:string)=>staticFile(`live-map-tracking-v2/${name}`);
const ease=(f:number,a:number,b:number)=>interpolate(f,[a,b],[0,1],{
  extrapolateLeft:"clamp",extrapolateRight:"clamp",easing:Easing.bezier(.35,0,.2,1)});
const mix=(a:number,b:number,t:number)=>a+(b-a)*t;

const clamp=(x:number,a:number,b:number)=>Math.min(b,Math.max(a,x));

function Marker({x,y,label,show=1}: {x:number;y:number;label:string;show?:number}) {
  return <div style={{position:"absolute",left:x,top:y,transform:"translate(-50%,-100%)",opacity:show,display:"grid",justifyItems:"center"}}>
    <div style={{background:paper,border:`2px solid ${orange}`,borderRadius:14,padding:"8px 14px",fontSize:23,fontWeight:800,whiteSpace:"nowrap"}}>{label}</div>
    <div style={{height:13,width:3,background:orange}}/>
    <div style={{height:11,width:11,borderRadius:10,background:orange,border:"2px solid white"}}/>
  </div>;
}
const first=staticFile("live-map-phase-v2/first.mp4");
const steps=["Source","En route","Destination"];
const modes=["Third-person","First-person","Local Follow"];
const subtitles=["See every task as it happens.","Robot, task, and route — in one view.","Track the movement in real time.","Switch perspectives to inspect the scene.","A connected view of every operation."];
const titles=["REAL-TIME VISIBILITY.","ACTIVE TASKS, CLEARLY CONNECTED.","FOLLOW THE ROBOT.","THREE VIEW MODES.","MONITOR. TRACK. RESPOND."];
const currentStep=(p:number)=>p>=1?2:p>0?1:0;

function TaskRail({progress,compact}: {progress:number;compact:boolean}) {
  const current=currentStep(progress);
  return <div style={{background:"#fffdf8",border:`1px solid ${line}`,borderRadius:20,overflow:"hidden"}}>
    <div style={{padding:"18px 27px",background:"#27201b",color:"white",display:"flex",justifyContent:"space-between",alignItems:"center",fontSize:23,fontWeight:750}}>
      <span>{progress>=1?"Task Status · F1":"Active Tasks · F1"}</span><span style={{color:"#ffb28d"}}>Robot M01</span>
    </div>
    <div style={{padding:compact?"20px 27px":"27px"}}>
      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
        <strong style={{fontSize:30,color:orange}}>T0002</strong>
        <span style={{background:"#ffebdd",color:"#8b3214",padding:"7px 12px",borderRadius:8,fontSize:19,fontWeight:750}}>{progress>=1?"Destination reached":"Executing"}</span>
      </div>
      <div style={{fontSize:42,fontWeight:800,lineHeight:1.08,marginTop:12}}>Medication Delivery</div>
      <div style={{fontSize:25,marginTop:15,color:muted}}>Pharmacy → Ward A</div>
      <div style={{fontSize:20,marginTop:19,color:muted}}>M01 location</div>
      <div style={{fontSize:26,fontWeight:780,marginTop:4}}>{progress>=1?"Ward A":progress>0?"Along the reference route":"Pharmacy"}</div>
    </div>
    <div style={{borderTop:`1px solid ${line}`,padding:"20px 26px 25px"}}>
      <div style={{fontSize:23,fontWeight:800,marginBottom:14}}>Task Progress</div>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:7}}>
        {steps.map((t,i)=><div key={t} style={{display:"grid",gap:8}}>
          <div style={{height:7,borderRadius:5,background:i===current?orange:i<current?"#433329":"#ddd1c8"}}/>
          <div style={{fontSize:19,fontWeight:i===current?850:650,color:i===current?"#963412":ink}}>{String(i+1).padStart(2,"0")} {t}</div>
        </div>)}
      </div>
    </div>
  </div>;
}

export const LiveMapPhaseV2=()=>{
  const f=useCurrentFrame();
  const scene=Math.min(4,Math.floor(f/90));
  const s=capture.frames[f];
  const caption=captions.find(({from,to})=>f>=from&&f<to);
  const open=ease(f,0,23);
  const panel=ease(f,87,110);
  const follow=ease(f,175,199);
  const end=ease(f,360,383);
  const mapX=mix(mix(mix(626,76,panel),76,follow),753,end);
  const mapW=mix(mix(mix(1217,1100,panel),1768,follow),1089,end);
  const angleLayout=ease(f,263,277)*(1-ease(f,359,382));
  const mapY=mix(mix(270,235,panel),248+52*angleLayout,follow);
  const mapH=mix(Math.min(mapW*9/16,686),570,angleLayout);
  const point=(xy:number[])=>{
    const scale=Math.max(mapW/1920,mapH/1080);
    return [clamp(xy[0]*scale+(mapW-1920*scale)/2,79,mapW-79),clamp(xy[1]*scale+(mapH-1080*scale)/2,92,mapH-20)];
  };
  const [rx,ry]=point(s.robot), [dx,dy]=point(s.destination);
  const entry=ease(f,204,219);
  const returnMap=ease(f,360,376);
  const firstPop=ease(f,279,292)*(1-ease(f,308,322));
  const selected=f<278?0:f<308?1:2;
  const comparison=ease(f,272,281)*(1-ease(f,311,322));
  const side=33.3333*comparison;
  return <AbsoluteFill style={{background:paper,color:ink,fontFamily:"Inter, Arial, Noto Sans CJK TC, sans-serif"}}>
    <div style={{position:"absolute",left:77,top:49,display:"flex",gap:10,alignItems:"center",fontSize:31,fontWeight:850}}>
      <Img src={staticFile("dashboard-v2/brand-mark.svg")} style={{width:43,height:36}} alt=""/><span>Medi<span style={{color:orange}}>Sync</span></span>
    </div>
    <div style={{position:"absolute",left:76,top:scene===0?305:115,width:scene===0?560:1680}}>
      <div style={{fontSize:scene===0?87:54,fontWeight:850,lineHeight:1.02,letterSpacing:scene===0?-4:-2,
        clipPath:scene===0?`inset(0 ${(1-open)*100}% 0 0)`:undefined}}>
        {scene===0?<>REAL-TIME<br/><span style={{color:orange}}>VISIBILITY.</span></>:titles[scene]}
      </div>
      <div style={{fontSize:scene===0?31:26,color:muted,marginTop:scene===0?21:11,fontWeight:600}}>{subtitles[scene]}</div>
      {scene===0&&<div style={{marginTop:36,fontSize:21,fontWeight:800,color:orange}}>F1 LIVE MAP</div>}
    </div>
    <div style={{position:"absolute",left:mapX,top:mapY,width:mapW,height:mapH,borderRadius:23,overflow:"hidden",border:`1px solid ${line}`,background:"#e9eceb"}}>
      <div style={{position:"absolute",top:0,left:0,width:scene===3&&f<322?`${100-2*side}%`:"100%",height:"100%",
        clipPath:f>=204&&f<219?`circle(${entry*148}% at ${100*rx/mapW}% ${100*ry/mapH}%)`:
          f>=360&&f<376?`circle(${returnMap*155}% at 50% 57%)`:undefined}}>
        <OffthreadVideo src={asset("map.mp4")} muted style={{width:"100%",height:"100%",objectFit:"cover"}}/>
      </div>
      {f>=204&&f<219&&<Img src={asset("overhead-handoff.jpg")} style={{position:"absolute",inset:0,width:"100%",height:"100%",objectFit:"cover",opacity:1-entry}}/>}
      {f>=360&&f<376&&<Img src={asset("follow-handoff.jpg")} style={{position:"absolute",inset:0,width:"100%",height:"100%",objectFit:"cover",opacity:1-returnMap}}/>}
      {f>=270&&f<322&&<>
        <div style={{position:"absolute",right:`${side}%`,width:`${side}%`,top:0,height:"100%",overflow:"hidden",borderLeft:`3px solid ${paper}`}}>
          <Sequence from={270} durationInFrames={52} layout="none"><OffthreadVideo src={first} muted style={{width:"100%",height:"100%",objectFit:"cover"}}/></Sequence>
          <div style={{position:"absolute",inset:0,border:`4px solid ${orange}`,opacity:firstPop,pointerEvents:"none"}}/>
        </div>
        <div style={{position:"absolute",right:0,width:`${side}%`,top:0,height:"100%",overflow:"hidden",borderLeft:`3px solid ${paper}`}}>
          <Sequence from={270} durationInFrames={52} layout="none"><OffthreadVideo src={asset("local.mp4")} muted style={{width:"100%",height:"100%",objectFit:"cover"}}/></Sequence>
        </div>
      </>}
      {f<204&&<Marker x={rx} y={ry} label={f>=56&&f<175?"M01 · Pharmacy":"M01"} show={ease(f,30,44)}/>}
      {f>=376&&<Marker x={rx} y={ry} label={s.progress>=1?"M01 · Ward A":"M01"} show={ease(f,376,391)}/>}
      {f<175&&<Marker x={dx} y={dy} label="Ward A" show={ease(f,51,70)}/>}
      {f>=186&&f<220&&<div style={{position:"absolute",left:clamp(rx+34,24,mapW-210),top:clamp(ry-61,30,mapH-74),
        opacity:ease(f,186,197)*(1-ease(f,209,220)),background:orange,color:"white",padding:"12px 19px",borderRadius:10,fontSize:23,fontWeight:800}}>Follow Robot</div>}
      {f>=220&&f<270&&<div style={{position:"absolute",left:23,top:23,background:paper,padding:"10px 15px",borderRadius:8,fontSize:22,fontWeight:750}}>Following M01 · Third-person</div>}
      {f>=94&&f<175&&<div style={{position:"absolute",left:23,bottom:18,background:paper,padding:"8px 12px",borderRadius:8,fontSize:18,fontWeight:750}}>Reference route · Simulated task</div>}
    </div>
    {scene===1&&<div style={{position:"absolute",left:1200,top:244,width:640,clipPath:`inset(0 0 ${(1-ease(f,98,123))*100}% 0)`}}><TaskRail progress={s.progress} compact={false}/></div>}
    {scene===4&&<div style={{position:"absolute",left:76,top:245,width:649,opacity:ease(f,362,383)}}><TaskRail progress={s.progress} compact/></div>}
    {scene===3&&<div style={{position:"absolute",left:76,right:76,top:226,display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:9,
      background:"#ede2d8",borderRadius:15,padding:7}}>
      {modes.map((m,i)=><div key={m} style={{fontSize:27,fontWeight:800,borderRadius:10,padding:"9px 18px",textAlign:"center",
        background:i===selected?orange:"#fff9f3",color:i===selected?"white":ink}}>{m}</div>)}
    </div>}
    {scene===3&&<div style={{position:"absolute",left:76,bottom:101,fontSize:19,color:muted,fontWeight:700}}>Simulated camera views</div>}
    {caption&&<div style={{position:"absolute",bottom:32,alignSelf:"center",background:ink,color:"white",padding:"9px 22px",borderRadius:8,fontSize:31}}>{caption.text}</div>}
    <Audio src={asset("voice.wav")}/><Audio src={asset("score.wav")}/>
  </AbsoluteFill>;
};
