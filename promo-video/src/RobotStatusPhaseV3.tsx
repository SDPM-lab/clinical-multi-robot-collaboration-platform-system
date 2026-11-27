import {AbsoluteFill,Audio,Img,staticFile,useCurrentFrame} from "remotion";
import {Cursor,FleetScroll,NativeCrop,Robot} from "./RobotStatusPhaseV2";
import capture from "./robot-status-phase-v2-capture.json";
import fleet from "./live-map-phase-v3-1-capture.json";
import captions from "./robot-status-phase-v3-captions.json";

const titles=["MEET YOUR ROBOT FLEET.","YOUR ROBOT. IN FOCUS.","EVERY DETAIL. AT A GLANCE.","CONNECTED ROBOT MANAGEMENT."];
const mix=(a:number,b:number,t:number)=>a+(b-a)*t;
const unit=(f:number,a:number,b:number)=>Math.min(1,Math.max(0,(f-a)/(b-a)));
const ease=(f:number,a:number,b:number)=>{
  const t=unit(f,a,b);
  return t*t*(3-2*t);
};
const stat=(file:string)=>staticFile("robot-status-phase-v2/"+file);
const paper="#faf7f3";
const page={x:112,y:103,scale:1.06};
const {list,m01:row,metrics,viewport}=capture;
const inspector={x:metrics.x-3,y:metrics.y-3,width:metrics.width+6,
  height:capture.controls.arm.y-21-(metrics.y-3)};
const marker=fleet.frames[fleet.frames.length-1].fleet[2].point;
const onMap={x:78+marker[0]*.917-145,y:194+(marker[1]-108)*.917-46};

export const RobotStatusPhaseV3=()=>{
  const f=useCurrentFrame();
  const chapter=f<90?0:f<180?1:f<300?2:3;
  const selected=f>=69;
  const source=selected?"m01":"c01";
  const listFocus=ease(f,22,37)*(1-ease(f,72,91));
  const scroll=capture.maxScroll*(1-Math.pow(1-unit(f,35,58),3))*(1-ease(f,70,89));
  const takeRobot=ease(f,82,103);
  const detail=ease(f,177,212);
  const dock=ease(f,300,332);
  const pageReturn=ease(f,316,333);
  const mapOut=ease(f,12,25);
  const idTravel=ease(f,8,30);
  const z=page.scale+.44*listFocus;
  const x=page.x+10*listFocus;
  const y=page.y-131*listFocus;
  const viewOrigin={x:page.x+viewport.x*page.scale,y:page.y+viewport.y*page.scale,
    w:viewport.width*page.scale,h:viewport.height*page.scale};
  const modalX=mix(374,86,detail), modalW=mix(1172,1020,detail);
  const viewportX=mix(mix(viewOrigin.x,modalX,takeRobot),viewOrigin.x,dock);
  const viewportY=mix(mix(viewOrigin.y,118,takeRobot),viewOrigin.y,dock);
  const viewportW=mix(mix(viewOrigin.w,modalW,takeRobot),viewOrigin.w,dock);
  const viewportH=mix(mix(viewOrigin.h,834,takeRobot),viewOrigin.h,dock);
  const inspectorX=mix(1163,page.x+inspector.x*page.scale,dock);
  const inspectorY=mix(143,page.y+inspector.y*page.scale,dock);
  const inspectorScale=mix(1.60,page.scale,dock);
  const cursor=ease(f,46,65);
  const press=ease(f,67,69)*(1-ease(f,69,73));
  const caption=captions.find(({from,to})=>f>=from&&f<to);
  const camera=mix(mix(132,209,ease(f,98,188)),132,ease(f,291,329));

  return <AbsoluteFill style={{background:paper,color:"#241e1a",fontFamily:"Inter,Arial,'Noto Sans CJK TC',sans-serif",overflow:"hidden"}}>
    <div style={{position:"absolute",left:112,top:25,fontSize:46,letterSpacing:-1.4,fontWeight:850}}>{titles[chapter]}</div>
    <div style={{position:"absolute",right:112,top:42,fontSize:15,fontWeight:650,color:"#69574b"}}>Demo Telemetry</div>
    <div style={{position:"absolute",left:x,top:y,width:1600,height:820,overflow:"hidden",
      transform:`scale(${z})`,transformOrigin:"0 0",borderRadius:14,
      boxShadow:"0 20px 64px #3c2b1e18",opacity:Math.max(1-takeRobot,pageReturn),
      clipPath:y<89?`inset(${(89-y)/z}px 0 0 0)`:undefined}}>
      <Img src={stat(source+".png")} style={{width:1600,height:820}}/>
      {f>=29&&f<90&&<FleetScroll f={f} source={source} scroll={scroll} hover={ease(f,61,67)*(1-ease(f,69,72))}/>}
    </div>
    {f>=76&&f<345&&<div style={{position:"absolute",left:viewportX,top:viewportY,width:viewportW,height:viewportH,
      overflow:"hidden",opacity:takeRobot*(1-ease(f,327,344)),
      background:`radial-gradient(ellipse at 49% 45%,#fff 2%,${paper} 70%)`}}>
      <Robot f={camera}/>
    </div>}
    {detail>0&&f<334&&<NativeCrop image="m01" box={inspector} style={{left:inspectorX,top:inspectorY,
      transform:`scale(${inspectorScale})`,transformOrigin:"0 0",borderRadius:11,opacity:1-ease(f,328,334),
      clipPath:`inset(0 0 0 ${100*(1-detail)}%)`}}/>}
    {f>=45&&f<80&&<Cursor x={mix(470,x+(row.x+row.width*.62)*z,cursor)}
      y={mix(288,y+(row.y+row.height*.50-scroll)*z,cursor)} press={press} opacity={1-ease(f,73,80)}/>}
    {f<25&&<Img src={staticFile("robot-status-phase-v1/live-map.png")} style={{position:"absolute",inset:0,width:"100%",height:"100%",opacity:1-mapOut}}/>}
    {f>=7&&f<35&&<div style={{position:"absolute",left:mix(onMap.x-45,x+(list.x+77)*z,idTravel),
      top:mix(onMap.y,y+(row.y+15)*z,idTravel),width:90,height:36,display:"grid",placeItems:"center",borderRadius:7,
      background:"#ffe7d8",border:"1px solid #ec985f",color:"#9a4120",fontSize:22,fontWeight:800,
      opacity:ease(f,7,11)*(1-ease(f,27,35))}}>M01</div>}
    {caption&&<div style={{position:"absolute",bottom:27,alignSelf:"center",borderRadius:8,padding:"7px 17px",
      background:"#231e1bea",color:"white",fontSize:30,fontWeight:650}}>{caption.text}</div>}
    <Audio src={staticFile("robot-status-phase-v3/voice.wav")}/>
    <Audio src={staticFile("robot-status-phase-v3/score.wav")}/>
  </AbsoluteFill>;
};
