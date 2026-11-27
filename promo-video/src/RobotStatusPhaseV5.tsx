import {AbsoluteFill,Audio,Img,cancelRender,staticFile,useCurrentFrame,useDelayRender} from "remotion";
import {useEffect,useLayoutEffect,useRef,useState} from "react";
import {Cursor,FleetScroll} from "./RobotStatusPhaseV2";
import {createRobotStatusScene} from "./robotStatusScene";
import capture from "./robot-status-phase-v2-capture.json";
import fleet from "./live-map-phase-v3-1-capture.json";
import captions from "./robot-status-phase-v5-captions.json";

const art=(name:string)=>staticFile("robot-status-phase-v5/"+name);
const old=(name:string)=>staticFile("robot-status-phase-v2/"+name);
const ink="#261f1a", orange="#ce501b", paper="#faf7f3";
const titles=["MANAGE YOUR ROBOT FLEET.","BROWSE. SELECT. EXPLORE.","INTERACTIVE 3D ROBOT VIEW.",
  "STATUS AT A GLANCE.","ONE CONNECTED PLATFORM."];
const unit=(f:number,a:number,b:number)=>Math.max(0,Math.min(1,(f-a)/(b-a)));
const ease=(f:number,a:number,b:number)=>{const t=unit(f,a,b);return t*t*(3-2*t);};
const mix=(a:number,b:number,t:number)=>a+(b-a)*t;
const {viewport,m01,metrics,maxScroll}=capture;

function WorkspaceModel({pose,opacity}:{pose:number;opacity:number}){
  const canvas=useRef<HTMLCanvasElement>(null);
  const scene=useRef<Awaited<ReturnType<typeof createRobotStatusScene>>|null>(null);
  const current=useRef(pose);
  const [ready,setReady]=useState(false);
  const {delayRender,continueRender}=useDelayRender();
  useLayoutEffect(()=>{current.current=pose;scene.current?.draw(pose);},[pose]);
  useEffect(()=>{
    const handle=delayRender("First frame of original Agibot GLB");
    let active=true;
    let released=false;
    const release=()=>{
      if(!released){released=true;continueRender(handle);}
    };
    createRobotStatusScene(canvas.current!,staticFile("ppo-spatial/AGIBOT_A2D.glb"),1,1,false,true)
      .then(value=>{
        if(!active){value.dispose();return;}
        scene.current=value;
        value.draw(current.current);
        setReady(true);
        release();
      }).catch(error=>{if(active)cancelRender(error);});
    return ()=>{
      active=false;
      scene.current?.dispose();
      scene.current=null;
      release();
    };
  },[continueRender,delayRender]);
  return <div style={{position:"absolute",left:viewport.x,top:viewport.y,width:viewport.width,height:viewport.height,
    overflow:"hidden",opacity:ready?opacity:0}}>
    <Img src={art("m01-viewport-clean.png")} style={{position:"absolute",left:-viewport.x,top:-viewport.y,width:1600,height:820}}/>
    <canvas ref={canvas} width={1186} height={996} style={{position:"absolute",inset:0,width:"100%",height:"100%"}}/>
  </div>;
}

export const RobotStatusPhaseV5=()=>{
  const f=useCurrentFrame();
  const chapter=f<60?0:f<150?1:f<240?2:f<300?3:4;
  const select=126;
  const source=f>=select?"m01":"c01";
  const browsing=ease(f,59,77)*(1-ease(f,134,153));
  const hero=ease(f,148,175)*(1-ease(f,234,249));
  const information=ease(f,237,254)*(1-ease(f,295,318));
  const hold=ease(f,300,326);
  const zoom=1.06+.16*browsing+.24*hero+.16*information-.06*hold;
  const pageX=112-18*browsing-133*hero-205*information+48*hold;
  const pageY=107-43*browsing-126*hero-40*information-17*hold;
  const scroll=maxScroll*(1-Math.pow(1-unit(f,74,107),3))*(1-ease(f,132,147));
  const pose=mix(132,203,ease(f,154,212))-71*ease(f,228,245);
  const modelOpacity=ease(f,150,164)*(1-ease(f,237,249));
  const cursor=ease(f,104,121);
  const click=ease(f,124,126)*(1-ease(f,126,131));
  const marker=fleet.frames[fleet.frames.length-1].fleet[2].point;
  const mapID={x:78+marker[0]*.917-145,y:194+(marker[1]-108)*.917-40};
  const transfer=ease(f,9,33);
  const caption=captions.find(c=>f>=c.from&&f<c.to);

  return <AbsoluteFill style={{background:paper,color:ink,fontFamily:"Inter,Arial,'Noto Sans CJK TC',sans-serif",overflow:"hidden"}}>
    <div style={{position:"absolute",left:112,top:25,fontSize:45,fontWeight:850,letterSpacing:-1.4}}>{titles[chapter]}</div>
    <div style={{position:"absolute",right:115,top:43,fontSize:15,color:"#735c4e",fontWeight:650}}>Demo Telemetry</div>
    <div style={{position:"absolute",left:pageX,top:pageY,width:1600,height:hold>0?930:820,overflow:"hidden",
      clipPath:pageY<85?`inset(${(85-pageY)/zoom}px 0 0 0 round 15px)`:"inset(0 round 15px)",
      transform:`scale(${zoom})`,transformOrigin:"0 0"}}>
      <Img src={old(source+".png")} style={{position:"absolute",left:0,top:0,width:1600,height:820}}/>
      {f>=74&&f<148&&<FleetScroll f={f} source={source} scroll={scroll}
        hover={ease(f,120,125)*(1-ease(f,126,130))}/>}
      {f>=145&&f<251&&<WorkspaceModel pose={pose} opacity={modelOpacity}/>}
      {information>0&&<div style={{position:"absolute",left:metrics.x-3,top:metrics.y-3,width:metrics.width+6,
        height:metrics.height+6,border:`2px solid ${orange}`,boxSizing:"border-box",borderRadius:13,pointerEvents:"none",
        opacity:.35*ease(f,247,257)*(1-ease(f,270,284))}}/>}
      {hold>0&&<Img src={art("m01-complete.png")} style={{position:"absolute",left:0,top:0,width:1600,height:930,opacity:hold}}/>}
    </div>
    {f>=102&&f<138&&<Cursor x={mix(482,pageX+(m01.x+m01.width*.65)*zoom,cursor)}
      y={mix(360,pageY+(m01.y+m01.height*.55-scroll)*zoom,cursor)} press={click} opacity={ease(f,102,108)*(1-ease(f,131,138))}/>}
    {f<26&&<Img src={staticFile("robot-status-phase-v1/live-map.png")}
      style={{position:"absolute",inset:0,width:1920,height:1080,opacity:1-ease(f,10,26)}}/>}
    {f>=6&&f<40&&<div style={{position:"absolute",left:mix(mapID.x-45,pageX+76*zoom,transfer),
      top:mix(mapID.y-24,pageY+(m01.y+12)*zoom,transfer),width:90,height:39,
      borderRadius:8,background:"#ffe7d8",color:"#994425",border:"1px solid #ec985f",
      display:"grid",placeItems:"center",fontSize:22,fontWeight:800,
      opacity:ease(f,6,12)*(1-ease(f,31,40))}}>M01</div>}
    {caption&&<div style={{position:"absolute",bottom:22,alignSelf:"center",background:"#231e1bea",color:"white",
      borderRadius:8,padding:"6px 16px",fontSize:29,fontWeight:650}}>{caption.text}</div>}
    <Audio src={art("voice.wav")}/><Audio src={art("score.wav")}/>
  </AbsoluteFill>;
};
