import { AbsoluteFill, Audio, Easing, Freeze, Img, OffthreadVideo, Sequence, cancelRender, interpolate, staticFile, useCurrentFrame, useDelayRender } from "remotion";
import { useEffect, useLayoutEffect, useRef } from "react";
import { RobotFleetCanvasV12 } from "./RobotFleetCanvasV12";
import { createRobotStatusScene } from "./robotStatusScene";
import captions from "./robot-status-phase-v12-captions.json";

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
  return <canvas ref={canvas} style={{display:"block",width:1070,height:898}}/>;
}

function Gauge({f,name,start,x,top,offset}:{f:number;name:string;start:number;x:number;top:number;offset:number}) {
  const p=move(f,start,start+23);
  if(f<start)return null;
  const depth=1-p;
  const battery=name==="battery";
  return <div style={{position:"absolute",left:x+offset*depth,top:top+(battery?12:-24)*depth,width:302,height:294,
    overflow:"hidden",borderRadius:18,opacity:p,transformOrigin:battery?"50% 55%":"50% 0%",
    transform:battery?`perspective(1200px) translateZ(${-55*depth}px) rotateY(${-3*depth}deg)`
      :`perspective(1250px) rotateX(${8*depth}deg)`,
    boxShadow:"0 14px 38px #43342411"}}>
    <Sequence from={start} layout="none">
      <Freeze frame={47} active={f>=start+47}>
        <OffthreadVideo muted src={asset(name+".mp4")} style={{width:302,height:294}}/>
      </Freeze>
    </Sequence>
  </div>;
}

export const RobotStatusPhaseV12=()=>{
  const f=useCurrentFrame();
  const mapFade=move(f,14,31);
  const modelIn=move(f,169,178);
  const robotYaw=.50-(210*Math.PI/180)*(1-move(f,168,248,Easing.out(Easing.cubic)));
  const info=move(f,270,298);
  const detailMix=move(f,184,200);
  const caption=captions.find(c=>f>=c.from&&f<c.to);

  return <AbsoluteFill style={{background:paper,color:ink,fontFamily:"Inter, Arial, 'Noto Sans CJK TC', sans-serif",overflow:"hidden"}}>
    {f<31&&<Img src={staticFile("robot-status-phase-v9/phase4-final.png")} style={{position:"absolute",width:1920,height:1080,
      opacity:1-mapFade,clipPath:`inset(${194*move(f,6,17)}px 0 0 0 round 0)`}}/>}
    <div style={{position:"absolute",left:76,top:51,display:"flex",alignItems:"center",gap:9,
      opacity:move(f,17,25),fontSize:28,fontWeight:850}}>
      <Img src={staticFile("dashboard-v2/brand-mark.svg")} style={{width:42,height:29}}/>
      <span>Medi<span style={{color:orange}}>Sync</span></span>
    </div>
    {f>=31&&f<185&&<RobotFleetCanvasV12 frame={f}/>}

    {f>=164&&<div style={{position:"absolute",left:1150,top:182,opacity:detailMix}}>
      <div style={{fontSize:19,fontWeight:760,letterSpacing:2.8,color:orange}}>ROBOT STATUS</div>
      <div style={{display:"flex",alignItems:"baseline",gap:20,marginTop:9}}>
        <strong style={{fontSize:56,letterSpacing:-2,lineHeight:1}}>M01</strong>
        <span style={{color:"#5b5048",fontSize:23}}>Agibot Genie G1</span>
      </div>
    </div>}
    <div style={{position:"absolute",left:66+46*(1-modelIn),top:133,opacity:modelIn,overflow:"hidden"}}>
      <OrbitingRobot angle={robotYaw}/>
    </div>

    <Gauge f={f} name="battery" start={238} x={1150} top={322} offset={-42}/>
    <Gauge f={f} name="temperature" start={251} x={1478} top={322} offset={30}/>
    {f>=269&&<section style={{position:"absolute",left:1150+32*(1-info),top:643+22*(1-info),width:630,
      padding:"22px 28px 19px",boxSizing:"border-box",borderRadius:17,background:"#fff2c9",opacity:info,
      clipPath:`inset(0 ${(1-info)*24}% 0 0 round 17px)`,boxShadow:"0 14px 38px #43342411"}}>
      <h2 style={{fontSize:24,margin:"0 0 10px"}}>Robot information</h2>
      {[["Operational status","Idle"],["Connection","Connected"],["Location","Ward A"]].map(([label,value])=>
        <div key={label} style={{display:"flex",justifyContent:"space-between",fontSize:20,padding:"10px 0",
          color:"#62574b",borderTop:"1px solid #e2d7b3"}}>
          {label}<strong style={{color:ink}}>{value}</strong>
        </div>)}
    </section>}

    {f>=297&&<span style={{position:"absolute",right:141,bottom:71,color:"#65594f",fontSize:15}}>Simulated telemetry</span>}
    {caption&&<div style={{position:"absolute",bottom:22,alignSelf:"center",background:"#25211e",color:"white",
      borderRadius:8,padding:"7px 16px",fontSize:28,fontWeight:650}}>{caption.text}</div>}
    <Audio src={asset("voice.wav")}/>
    <Audio src={asset("score.wav")}/>
  </AbsoluteFill>;
};
