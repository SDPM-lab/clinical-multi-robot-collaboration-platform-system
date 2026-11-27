import {AbsoluteFill,Audio,Img,staticFile,useCurrentFrame} from "remotion";
import {Cursor,FleetScroll} from "./RobotStatusPhaseV2";
import capture from "./robot-status-phase-v2-capture.json";
import captions from "./robot-status-phase-v6-captions.json";

const native=(file:string)=>staticFile("robot-status-phase-v2/"+file);
const audio=(file:string)=>staticFile("robot-status-phase-v6/"+file);
const {list,viewport,metrics,information,m01,maxScroll}=capture;
const workspace={x:60,y:45,scale:1.125};
const unit=(frame:number,from:number,to:number)=>Math.min(1,Math.max(0,(frame-from)/(to-from)));
const mix=(a:number,b:number,t:number)=>a+(b-a)*t;
const ease=(f:number,a:number,b:number)=>{
  const t=unit(f,a,b);
  return t*t*(3-2*t);
};
const outlines=[
  {box:list,start:38,full:53,hold:80,end:94},
  {box:viewport,start:94,full:101,hold:106,end:112},
  {box:metrics,start:112,full:119,hold:124,end:131},
  {box:information,start:131,full:138,hold:143,end:150},
];
const toScreen=(x:number,y:number)=>({x:workspace.x+x*workspace.scale,y:workspace.y+y*workspace.scale});

export const RobotStatusPhaseV6=()=>{
  const f=useCurrentFrame();
  const source=f<91?"c01":"m01";
  const scrollProgress=unit(f,47,77);
  const scroll=maxScroll*(1-(1-scrollProgress)**3);
  const cursorTarget=toScreen(m01.x+m01.width*.58,m01.y+m01.height*.5-scroll);
  const cursorList=toScreen(list.x+list.width*.72,list.y+180);
  const pointerArrive=ease(f,34,46), pointerSelect=ease(f,77,87);
  const movingX=mix(mix(745,cursorList.x,pointerArrive),cursorTarget.x,pointerSelect);
  const movingY=mix(mix(397,cursorList.y,pointerArrive),cursorTarget.y,pointerSelect);
  const press=ease(f,89,91)*(1-ease(f,91,95));
  const caption=captions.find(line=>f>=line.from&&f<line.to);
  const highlight=outlines.find(({start,end})=>f>=start&&f<end);

  return <AbsoluteFill style={{background:"#faf7f3",color:"#261f1a",fontFamily:"Inter,Arial,'Noto Sans CJK TC',sans-serif",overflow:"hidden"}}>
    <div style={{position:"absolute",left:workspace.x,top:workspace.y,width:1600,height:820,
      transform:`scale(${workspace.scale})`,transformOrigin:"0 0",overflow:"hidden",borderRadius:15,
      boxShadow:"0 12px 38px #47332619"}}>
      <Img src={native(source+".png")} style={{position:"absolute",inset:0,width:"100%",height:"100%"}}/>
      {f>=47&&<FleetScroll f={f} source={source} scroll={scroll} hover={0}/>}
      {highlight&&<svg viewBox="0 0 1600 820" width="1600" height="820"
        style={{position:"absolute",inset:0,pointerEvents:"none"}}>
        <rect x={highlight.box.x-2} y={highlight.box.y-2} width={highlight.box.width+4} height={highlight.box.height+4}
          rx="11" pathLength="1" fill="none" stroke="#df611d" strokeWidth="2"
          strokeDasharray="1 1" strokeDashoffset={1-ease(f,highlight.start,highlight.full)}
          opacity={1-ease(f,highlight.hold,highlight.end)}/>
      </svg>}
    </div>
    <span style={{position:"absolute",right:66,top:17,fontSize:14,fontWeight:650,color:"#735c4e"}}>Demo Telemetry</span>
    {f>=34&&f<100&&<Cursor x={movingX} y={movingY} press={press}
      opacity={ease(f,34,39)*(1-ease(f,94,100))}/>}
    {f<4&&<Img src={staticFile("robot-status-phase-v1/live-map.png")}
      style={{position:"absolute",inset:0,width:1920,height:1080}}/>}
    {caption&&<div style={{position:"absolute",bottom:22,alignSelf:"center",background:"#231e1bea",color:"white",
      borderRadius:7,padding:"5px 16px",fontSize:28,fontWeight:650}}>{caption.text}</div>}
    <Audio src={audio("voice.wav")}/>
    <Audio src={audio("score.wav")}/>
  </AbsoluteFill>;
};
