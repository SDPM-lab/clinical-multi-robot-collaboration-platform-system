import { AbsoluteFill, Audio, Easing, Freeze, Img, OffthreadVideo, Sequence, cancelRender, interpolate, staticFile, useCurrentFrame, useDelayRender } from "remotion";
import { useEffect, useLayoutEffect, useRef } from "react";
import { RobotFleetCanvasV13 } from "./RobotFleetCanvasV13";
import { createRobotStatusScene } from "./robotStatusScene";
import captions from "./robot-status-phase-v13-captions.json";

const asset=(name:string)=>staticFile(`robot-status-phase-v12/${name}`);
const paper="#faf7f2", ink="#211d19", orange="#b7491d";
const soft=Easing.bezier(.33,0,.23,1);
const move=(f:number,start:number,end:number,easing=soft)=>
  interpolate(f,[start,end],[0,1],{easing,extrapolateLeft:"clamp",extrapolateRight:"clamp"});
function OrbitingRobot({angle}:{angle:number}) {
  const canvas=useRef<HTMLCanvasElement>(null);
  const scene=useRef<Awaited<ReturnType<typeof createRobotStatusScene>>|null>(null);
  const lastAngle=useRef(angle);
  const {delayRender,continueRender}=useDelayRender();
  useLayoutEffect(()=>{
    lastAngle.current=angle;
    scene.current?.drawOrbit(angle);
  },[angle]);
  useEffect(()=>{
    const loading=delayRender("Load original Agibot GLB before the fleet handoff");
    let active=true;
    createRobotStatusScene(canvas.current!,staticFile("ppo-spatial/AGIBOT_A2D.glb"),1,1,false,true)
      .then(renderer=>{
        if(!active){renderer.dispose();return;}
        scene.current=renderer;
        renderer.drawOrbit(lastAngle.current);
        continueRender(loading);
      }).catch(error=>{if(active)cancelRender(error);});
    return ()=>{
      active=false;
      scene.current?.dispose();
      scene.current=null;
      continueRender(loading);
    };
  },[delayRender,continueRender]);
  return <canvas ref={canvas} style={{display:"block",width:1000,height:840}}/>;
}

function Gauge({f,name,start,x,top,offset}:{f:number;name:string;start:number;x:number;top:number;offset:number}) {
  const p=move(f,start,start+23);
  if(f<start)return null;
  const depth=1-p;
  const battery=name==="battery";
  return <div style={{position:"absolute",left:x+offset*depth,top:top+(battery?12:-24)*depth,width:250,height:244,
    overflow:"hidden",borderRadius:18,opacity:p,transformOrigin:battery?"50% 55%":"50% 0%",
    transform:battery?`perspective(1200px) translateZ(${-55*depth}px) rotateY(${-3*depth}deg)`
      :`perspective(1250px) rotateX(${8*depth}deg)`,
    boxShadow:"0 14px 38px #43342411"}}>
    <Sequence from={start} layout="none">
      <Freeze frame={47} active={f>=start+47}>
        <OffthreadVideo muted src={asset(name+".mp4")} style={{width:250,height:244}}/>
      </Freeze>
    </Sequence>
  </div>;
}

export const RobotStatusPhaseV13=()=>{
  const f=useCurrentFrame();
  const mapFade=move(f,12,34);
  const modelIn=move(f,195,207);
  const robotYaw=.72-(175*Math.PI/180)*(1-move(f,194,264,Easing.bezier(.23,.65,.30,1)));
  const info=move(f,274,298);
  const heading=move(f,247,263);
  const arrow=move(f,187,232);
  const arrowOpacity=move(f,187,192)*(1-move(f,228,251));
  const caption=captions.find(c=>f>=c.from&&f<c.to);

  return <AbsoluteFill style={{background:paper,color:ink,fontFamily:"Inter, Arial, 'Noto Sans CJK TC', sans-serif",overflow:"hidden"}}>
    {f<34&&<Img src={staticFile("robot-status-phase-v9/phase4-final.png")} style={{position:"absolute",width:1920,height:1080,
      opacity:1-mapFade,clipPath:`inset(${194*move(f,6,17)}px 0 0 0 round 0)`}}/>}
    <div style={{position:"absolute",left:76,top:51,display:"flex",alignItems:"center",gap:9,
      opacity:move(f,17,25),fontSize:28,fontWeight:850}}>
      <Img src={staticFile("dashboard-v2/brand-mark.svg")} style={{width:42,height:29}}/>
      <span>Medi<span style={{color:orange}}>Sync</span></span>
    </div>
    {f>=36&&f<213&&<RobotFleetCanvasV13 frame={f}/>}

    <div style={{position:"absolute",left:26+36*(1-modelIn),top:164,opacity:modelIn,overflow:"hidden"}}>
      <OrbitingRobot angle={robotYaw}/>
    </div>

    {f>=247&&<div style={{position:"absolute",left:78,top:123+10*(1-heading),opacity:heading}}>
      <div style={{fontSize:54,fontWeight:820,letterSpacing:-2.5}}>YOUR FLEET. AT A GLANCE.</div>
      <div style={{fontSize:23,marginTop:9,color:"#65594f"}}>Monitor robot health, availability and operational details.</div>
    </div>}
    {f>=187&&f<251&&<svg width={1920} height={1080} style={{position:"absolute",inset:0,opacity:arrowOpacity}} aria-hidden>
      <path d="M 371 543 C 460 563 367 890 593 922 C 760 947 908 862 1016 811"
        fill="none" stroke="#d36c2f" strokeWidth={3} strokeLinecap="round" pathLength={1}
        strokeDasharray="1 1" strokeDashoffset={1-arrow} />
      {f>=229&&<path d="M 998 813 L 1016 811 L 1007 827" fill="none" stroke="#d36c2f" strokeWidth={3}
        strokeLinejoin="round" strokeLinecap="round" opacity={move(f,229,233)}/>}
    </svg>}
    <Gauge f={f} name="battery" start={249} x={1110} top={277} offset={-36}/>
    <Gauge f={f} name="temperature" start={260} x={1463} top={277} offset={27}/>
    {f>=274&&<section style={{position:"absolute",left:1030+26*(1-info),top:552+12*(1-info),width:790,
      padding:"24px 28px",boxSizing:"border-box",borderRadius:20,background:"#fff2cf",opacity:info,
      clipPath:`inset(0 ${(1-info)*20}% 0 0 round 20px)`,boxShadow:"0 18px 42px #43342412"}}>
      <header style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:14}}>
        <h2 style={{fontSize:27,margin:0}}>Robot information</h2>
        <span style={{color:"#39654e",fontSize:18,fontWeight:740}}>Idle</span>
      </header>
      <dl style={{display:"grid",gridTemplateColumns:"1fr 1fr",columnGap:31,margin:0}}>
        {[["Robot ID","M01"],["Connection","Connected"],["Manufacturer","Agibot"],["Model","Agibot Genie G1"],
          ["Robot type","Medical"],["Current floor","1F"],["Current location","Ward A"],["Current task ID","—"]].map(([label,value],i)=>
          <div key={label} style={{borderTop:"1px solid #e3d6b6",padding:"11px 0 12px",opacity:move(f,278+2*Math.floor(i/2),293+2*Math.floor(i/2))}}>
            <dt style={{color:"#665a4c",fontSize:16}}>{label}</dt>
            <dd style={{fontSize:23,fontWeight:720,margin:"5px 0 0",whiteSpace:"nowrap"}}>{value}</dd>
          </div>)}
      </dl>
    </section>}
    {f>=299&&<span style={{position:"absolute",right:101,bottom:77,color:"#65594f",fontSize:15}}>Simulated telemetry</span>}
    {caption&&<div style={{position:"absolute",bottom:22,alignSelf:"center",background:"#25211e",color:"white",
      borderRadius:8,padding:"7px 16px",fontSize:28,fontWeight:650}}>{caption.text}</div>}
    <Audio src={staticFile("robot-status-phase-v13/voice.wav")}/>
    <Audio src={staticFile("robot-status-phase-v13/score.wav")}/>
  </AbsoluteFill>;
};
