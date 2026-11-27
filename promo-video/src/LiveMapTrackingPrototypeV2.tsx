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
const titles=["REAL-TIME VISIBILITY.","EVERY TASK. IN SIGHT.","FOLLOW EVERY MOVE.","MULTIPLE PERSPECTIVES.","MONITOR. TRACK. RESPOND."];
const clamp=(x:number,a:number,b:number)=>Math.min(b,Math.max(a,x));

function Marker({x,y,label,show=1}: {x:number;y:number;label:string;show?:number}) {
  return <div style={{position:"absolute",left:x,top:y,transform:"translate(-50%,-100%)",opacity:show,display:"grid",justifyItems:"center"}}>
    <div style={{background:paper,border:`2px solid ${orange}`,borderRadius:14,padding:"8px 14px",fontSize:23,fontWeight:800,whiteSpace:"nowrap"}}>{label}</div>
    <div style={{height:13,width:3,background:orange}}/>
    <div style={{height:11,width:11,borderRadius:10,background:orange,border:"2px solid white"}}/>
  </div>;
}
function TaskPanel({f,final=false,progress}: {f:number;final?:boolean;progress:number}) {
  const show=final?ease(f,369,393):ease(f,106,128);
  const detail=final?show:ease(f,125,149);
  const steps=final?show:ease(f,144,164);
  return <div style={{position:"absolute",top:final?265:244,left:final?84:1200,width:final?625:630,opacity:show,
    background:"#fffdf9",border:`1px solid ${line}`,borderRadius:21,overflow:"hidden"}}>
    <div style={{padding:"22px 27px",fontSize:23,fontWeight:800,borderBottom:`1px solid ${line}`,display:"flex",justifyContent:"space-between"}}>
      <span>{progress>=1?"Task status · F1":"Active Tasks · F1"}</span>
      <span style={{color:orange}}>M01</span>
    </div>
    <div style={{padding:"24px 27px 26px",opacity:detail}}>
      <div style={{fontSize:28,color:orange,fontWeight:800}}>T0002</div>
      <div style={{fontSize:40,fontWeight:780,letterSpacing:-1,margin:"6px 0 14px"}}>Medication Delivery</div>
      <div style={{display:"flex",alignItems:"center",gap:12,color:muted,fontSize:24}}>
        <span>Pharmacy → Ward A</span><span style={{marginLeft:"auto",background:"#fbe9de",color:"#942f10",borderRadius:7,padding:"5px 9px",
          fontSize:18,fontWeight:750}}>{progress>=1?"Destination reached":"Executing"}</span>
      </div>
    </div>
    <div style={{borderTop:`1px solid ${line}`,padding:"21px 27px 24px",opacity:steps}}>
      <div style={{fontSize:23,fontWeight:800,marginBottom:11}}>Task Progress</div>
      {["Source · Pharmacy","En route","Destination · Ward A"].map((s,i)=>{
        const active=i===0 || (i===1&&progress>0) || (i===2&&progress>=1);
        return <div key={s} style={{fontSize:21,display:"flex",alignItems:"center",gap:12,lineHeight:"37px",color:active?ink:muted}}>
          <span style={{width:11,height:11,borderRadius:9,background:active?orange:"#d8cfc8"}}/>{s}
        </div>;
      })}
    </div>
  </div>;
}

export const LiveMapTrackingPrototypeV2 = () => {
  const f=useCurrentFrame();
  const s=capture.frames[f];
  const segment=Math.min(4,Math.floor(f/90));
  const caption=captions.find(({from,to})=>f>=from&&f<to);
  const titleIntro=ease(f,0,20);
  const toTasks=ease(f,79,103);
  const focus=ease(f,177,201);
  const returning=ease(f,360,381);
  const split=.48*ease(f,270,287)+.52*ease(f,305,322);
  const left=mix(mix(mix(701,80,toTasks),83,focus),752,returning);
  const width=mix(mix(mix(1160,1090,toTasks),1754,focus),1090,returning);
  const top=mix(mix(mix(232,237,toTasks),159,focus),273,returning);
  const height=width*9/16;
  const displayHeight=Math.min(height,781);
  const position=(p:number[])=>[clamp(p[0]*width/1920,88,width-88),clamp(p[1]*height/1080-(height-displayHeight)/2,90,displayHeight-18)];
  const [rx,ry]=position(s.robot);
  const [sx,sy]=position(s.source);
  const [dx,dy]=position(s.destination);
  const iris=ease(f,204,222);
  const toMap=ease(f,360,379);
  const anchorX=`${100*rx/width}%`;
  const anchorY=`${100*ry/displayHeight}%`;
  return <AbsoluteFill style={{background:paper,fontFamily:"Inter, Arial, Noto Sans CJK TC, sans-serif",color:ink}}>
    <div style={{position:"absolute",left:84,top:55,display:"flex",alignItems:"center",gap:12,fontSize:31,fontWeight:800}}>
      <Img src={staticFile("dashboard-v2/brand-mark.svg")} style={{width:44,height:36}} alt=""/><span>Medi<span style={{color:orange}}>Sync</span></span>
    </div>
    <span style={{position:"absolute",right:85,top:67,fontSize:20,color:muted,fontWeight:750,letterSpacing:1.2}}>LIVE MAP · SIMULATED TASK</span>
    {segment===0?
      <div style={{position:"absolute",left:78,top:318,width:610,clipPath:`inset(0 ${(1-titleIntro)*100}% 0 0)`}}>
        <div style={{fontSize:108,fontWeight:850,letterSpacing:-6,lineHeight:.91}}>REAL-TIME<br/><span style={{color:orange}}>VISIBILITY.</span></div>
        <div style={{fontSize:31,fontWeight:600,marginTop:30}}>One map. Every robot. Every task.</div>
      </div>:
      <div style={{position:"absolute",left:84,top:segment===4?136:103,fontSize:segment===4?57:47,lineHeight:1.08,fontWeight:850,
        letterSpacing:-1.8,opacity:segment===1?ease(f,90,104):1}}>
        {titles[segment]}
        {segment===4&&<div style={{fontSize:27,fontWeight:600,marginTop:5,letterSpacing:0,color:muted}}>A connected view of every operation.</div>}
      </div>}
    <div style={{position:"absolute",left,top,width,height:displayHeight,borderRadius:23,overflow:"hidden",background:"#e9eceb",
      border:`1px solid ${line}`,boxShadow:"0 10px 32px #281b1614"}}>
      <div style={{position:"absolute",left:0,top:0,height:"100%",width:f>=270&&f<322?`${100*(1-split)}%`:"100%",clipPath:f>=204&&f<222?`circle(${iris*150}% at ${anchorX} ${anchorY})`:
        f>=360&&f<379?`circle(${toMap*150}% at 60% 52%)`:undefined}}>
        <OffthreadVideo src={asset("map.mp4")} muted style={{width:"100%",height:"100%",objectFit:"cover"}}/>
      </div>
      {f>=204&&f<222&&<Img src={asset("overhead-handoff.jpg")} style={{
        position:"absolute",width:"100%",height:"100%",objectFit:"cover",
        opacity:1-iris,pointerEvents:"none"}}/>}
      {f>=360&&f<379&&<Img src={asset("follow-handoff.jpg")} style={{position:"absolute",width:"100%",height:"100%",objectFit:"cover",opacity:1-toMap}}/>}
      {f>=270&&f<322&&<div style={{position:"absolute",right:0,top:0,width:`${100*split}%`,height:"100%",overflow:"hidden"}}>
        <Sequence from={270} durationInFrames={52} layout="none">
          <OffthreadVideo src={asset("local.mp4")} muted style={{width:"100%",height:"100%",objectFit:"cover"}}/>
        </Sequence>
      </div>}
      {f>=270&&f<322&&split>.04&&split<.98&&<div style={{position:"absolute",right:`${100*split}%`,top:0,bottom:0,width:4,background:paper}}/>}
      {(f<204||f>=374)&&<Marker x={rx} y={ry} label={s.progress>=1?"M01 · Ward A":"M01"} show={f>=374?ease(f,374,391):ease(f,75,93)}/>}
      {f>=93&&f<180&&<>
        <Marker x={sx} y={sy} label="Pharmacy" show={ease(f,94,109)}/>
        <Marker x={dx} y={dy} label="Ward A" show={ease(f,103,118)}/>
      </>}
      {f>=184&&f<224&&<div style={{position:"absolute",left:clamp(rx+28,27,width-221),top:clamp(ry-74,32,displayHeight-100),
        opacity:ease(f,188,200)*(1-ease(f,216,224)),background:orange,color:"#fff",fontSize:24,fontWeight:800,borderRadius:12,padding:"13px 19px"}}>Follow Robot</div>}
      {f>=222&&f<360&&(f<270||f>=322||split<.86)&&<div style={{position:"absolute",left:24,top:24,padding:"10px 15px",background:paper,borderRadius:10,fontSize:22,fontWeight:800}}>
        {f<322?"Third-person View":"Local Follow View"}
      </div>}
      {f>=270&&f<322&&split>.24&&<div style={{position:"absolute",right:24,top:24,padding:"10px 15px",background:paper,borderRadius:10,fontSize:22,fontWeight:800}}>Local Follow View</div>}
      {f<180&&<div style={{position:"absolute",left:19,bottom:17,background:paper,borderRadius:9,padding:"8px 12px",fontSize:18,fontWeight:750}}>F1 · {f<105?"Hospital Live Map":"Reference Route"}</div>}
    </div>
    {segment===1&&<TaskPanel f={f} progress={s.progress}/>}
    {segment===4&&<TaskPanel f={f} progress={s.progress} final/>}
    {caption&&<div style={{position:"absolute",bottom:33,alignSelf:"center",padding:"9px 22px",borderRadius:8,background:ink,color:"white",fontSize:31}}>{caption.text}</div>}
    <Audio src={asset("voice.wav")}/>
    <Audio src={asset("score.wav")}/>
  </AbsoluteFill>;
};
