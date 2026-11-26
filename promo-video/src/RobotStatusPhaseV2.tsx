import {AbsoluteFill, Audio, Img, cancelRender, staticFile, useCurrentFrame, useDelayRender} from "remotion";
import {useEffect,useLayoutEffect,useRef} from "react";
import type {CSSProperties} from "react";
import {createRobotStatusScene} from "./robotStatusScene";
import subtitles from "./robot-status-phase-v2-captions.json";
import capture from "./robot-status-phase-v2-capture.json";
import fleetCapture from "./live-map-phase-v3-1-capture.json";

type Box={x:number;y:number;width:number;height:number};
const asset=(name:string)=>staticFile(`robot-status-phase-v2/${name}`);
const paper="#faf7f3", ink="#241e1a", orange="#d65720";
const pageWidth=1600, pageHeight=820;
const titles=["EVERY ROBOT. ONE PLATFORM.","EXPLORE YOUR ROBOT FLEET.","INTERACTIVE 3D ROBOT.",
  "EVERY DETAIL. IN VIEW.","EXPLORE EVERY COMPONENT.","COMPLETE ROBOT VISIBILITY."];
const lerp=(a:number,b:number,t:number)=>a+(b-a)*t;
const ease=(frame:number,a:number,b:number)=>{
  const t=Math.min(1,Math.max(0,(frame-a)/(b-a)));
  return t*t*t*(10+t*(-15+6*t));
};
const position=(x:number,y:number,width:number,height:number):CSSProperties=>
  ({position:"absolute",left:x,top:y,width,height});
const area=({x,y,width,height}:Box)=>position(x,y,width,height);

export function NativeCrop({image,box,style,children}:{image:string;box:Box;style?:CSSProperties;children?:React.ReactNode}){
  return <div style={{...area(box),overflow:"hidden",...style}}>
    <Img src={asset(image+".png")} style={position(-box.x,-box.y,pageWidth,pageHeight)}/>
    {children}
  </div>;
}

export function Robot({f,showcase=false}:{f:number;showcase?:boolean}){
  const canvas=useRef<HTMLCanvasElement>(null);
  const scene=useRef<Awaited<ReturnType<typeof createRobotStatusScene>>|null>(null);
  const latest=useRef(f);
  const {delayRender,continueRender}=useDelayRender();
  useLayoutEffect(()=>{latest.current=f;scene.current?.draw(f);},[f]);
  useEffect(()=>{
    const handle=delayRender("Loading original Agibot GLB");
    let active=true;
    createRobotStatusScene(canvas.current!,staticFile("ppo-spatial/AGIBOT_A2D.glb"),1.12,1.24,showcase).then(value=>{
      if(!active){value.dispose();return;}
      scene.current=value;
      value.draw(latest.current);
      continueRender(handle);
    }).catch(error=>{if(active)cancelRender(error);});
    return ()=>{
      active=false;
      scene.current?.dispose();
      scene.current=null;
      continueRender(handle);
    };
  },[continueRender,delayRender,showcase]);
  return <canvas ref={canvas} width={showcase?1440:830} height={showcase?800:720} style={{width:"100%",height:"100%",objectFit:"contain",display:"block"}}/>;
}

export function Cursor({x,y,press,opacity=1}:{x:number;y:number;press:number;opacity?:number}){
  return <svg width="24" height="29" viewBox="0 0 22 27" style={{...position(x,y,24,29),opacity,
    transform:`scale(${1-.17*press})`,transformOrigin:"0 0",pointerEvents:"none",filter:"drop-shadow(0 1px 2px #20171055)"}}>
    <path d="M2 1 2 21 7 17 11 25 15 23 11 15 20 14Z" fill="#22201d" stroke="white" strokeWidth="1.6" strokeLinejoin="round"/>
  </svg>;
}

const list=capture.list;
const row=capture.m01;
const info=capture.information;
const stage=capture.viewport;
const page={x:112,y:103,scale:1.06};
const scaleBox=(x:number,y:number,scale:number,box:Box)=>({x:x+box.x*scale,y:y+box.y*scale,width:box.width*scale,height:box.height*scale});
const scrollEnd=capture.maxScroll;
const cropBottom=4;
const strip={...list,height:list.height-cropBottom};

export function FleetScroll({f,source,scroll=scrollEnd*(1-Math.pow(1-ease(f,102,138),2))*(1-ease(f,158,171)),hover=ease(f,142,152)*(1-ease(f,153,158))}:{f:number;source:string;scroll?:number;hover?:number}){
  const split=Math.max(0,list.height-scroll);
  const areaEnd=Math.max(0,strip.height-split);
  return <>
    <NativeCrop image={source} box={strip} style={{height:Math.min(strip.height,split)}}>
      <Img src={asset(source+".png")} style={position(-list.x,-list.y-scroll,pageWidth,pageHeight)}/>
    </NativeCrop>
    {areaEnd>0&&<NativeCrop image="c01-scroll" box={{...strip,y:list.y+split,height:areaEnd}}>
      <Img src={asset("c01-scroll.png")} style={position(-list.x,-list.y-split-scroll+scrollEnd,pageWidth,pageHeight)}/>
    </NativeCrop>}
    <div style={{...position(row.x,row.y-scroll,row.width,row.height),borderRadius:9,background:"#e7853a13",
      opacity:hover,pointerEvents:"none"}}/>
  </>;
}

export const RobotStatusPhaseV2=()=>{
  const f=useCurrentFrame();
  const chapter=f<90?0:f<180?1:f<300?2:f<420?3:f<540?4:5;
  const source=f<154?"c01":"m01";
  const entering=ease(f,30,78);
  const closeList=ease(f,89,105)*(1-ease(f,158,183));
  const robotReveal=ease(f,176,195)*(1-ease(f,526,555));
  const context=ease(f,293,312)*(1-ease(f,410,431));
  const controlsFocus=ease(f,411,431)*(1-ease(f,526,548));
  const focusPart=f<429?"whole":f<466?"head":f<509?"arm":"whole";
  const modelFrame=f<300?lerp(132,209,ease(f,190,293)):f<429?209:f<466?lerp(453,482,ease(f,429,455)):
    f<509?lerp(484,518,ease(f,466,497)):lerp(521,549,ease(f,509,535));
  const zoom=lerp(1.30,page.scale,entering)+.60*closeList;
  const pageX=lerp(34,page.x,entering)+35*closeList;
  const pageY=lerp(11,page.y,entering)-136*closeList;
  const originalViewport=scaleBox(page.x,page.y,page.scale,stage);
  const view={x:lerp(originalViewport.x,context>0?lerp(460,100,context):460,robotReveal)-90*controlsFocus,
    y:lerp(originalViewport.y,143,robotReveal),width:lerp(originalViewport.width,945,robotReveal)-126*controlsFocus,
    height:lerp(originalViewport.height,820,robotReveal)};
  const scroll=scrollEnd*(1-Math.pow(1-ease(f,102,138),2));
  const hover={x:pageX+(row.x+row.width*.56)*zoom,y:pageY+(row.y+row.height*.55-scroll)*zoom};
  const cursorIn=ease(f,96,144);
  const voice=subtitles.find(c=>f>=c.from&&f<c.to);
  const controlTop=capture.controls.arm.y-31;
  const controlBottom=capture.controls.whole.y+capture.controls.whole.height+7;
  const controlsBox={x:info.x+9,y:controlTop,width:info.width-18,height:controlBottom-controlTop};
  const panelArea={x:info.x-6,y:capture.metrics.y-4,width:info.width+12,
    height:info.y+info.height-capture.metrics.y+9};
  const partSource=focusPart==="whole"?"m01":focusPart;
  const inspect=ease(f,339,369);
  const controlScale=1.43;
  const controlPoint=(box:Box)=>({
    x:(box.x+box.width*.58-controlsBox.x)*controlScale,
    y:(box.y+box.height*.54-controlsBox.y)*controlScale,
  });
  const head=controlPoint(capture.controls.head), arm=controlPoint(capture.controls.arm), whole=controlPoint(capture.controls.whole);
  const moveToHead=ease(f,419,429), moveToArm=ease(f,454,466), moveToWhole=ease(f,495,509);
  const cursorX=lerp(head.x+38,head.x,moveToHead)+(arm.x-head.x)*moveToArm+(whole.x-arm.x)*moveToWhole;
  const cursorY=lerp(head.y+63,head.y,moveToHead)+(arm.y-head.y)*moveToArm+(whole.y-arm.y)*moveToWhole;
  const m01=fleetCapture.frames[fleetCapture.frames.length-1].fleet[2].point;
  const mapLabelX=78+m01[0]*.917-145;
  const mapLabelY=194+(m01[1]-108)*.917-16;
  const shotOpacity=1-robotReveal;
  const click=ease(f,153,155)*(1-ease(f,155,159));
  const controlClick=[429,466,509].map(at=>ease(f,at-1,at+1)*(1-ease(f,at+1,at+5))).reduce((a,b)=>Math.max(a,b),0);
  const mapFade=1-ease(f,22,53);
  const handoff=ease(f,15,66);

  return <AbsoluteFill style={{background:paper,color:ink,fontFamily:"Inter,Arial,'Noto Sans CJK TC',sans-serif",overflow:"hidden"}}>
    <div style={{position:"absolute",left:112,top:23,fontSize:43,letterSpacing:-1.4,fontWeight:850}}>{titles[chapter]}</div>
    <div style={{position:"absolute",right:112,top:39,color:"#69574b",fontSize:15,fontWeight:650}}>Demo Telemetry</div>
    <div style={{...position(pageX,pageY,pageWidth,pageHeight),transform:`scale(${zoom})`,transformOrigin:"0 0",
      borderRadius:14,overflow:"hidden",boxShadow:"0 20px 64px #3c2b1e18",opacity:shotOpacity,
      clipPath:pageY<86?`inset(${(86-pageY)/zoom}px 0 0 0)`:undefined}}>
      <Img src={asset(source+".png")} style={position(0,0,pageWidth,pageHeight)}/>
      {f>=96&&f<174&&<FleetScroll f={f} source={source}/>}
    </div>

    {f>=170&&f<555&&<div style={{...area(view),opacity:robotReveal,overflow:"hidden",borderRadius:19,
      background:"radial-gradient(ellipse at 46% 50%,#fff 8%,#f0ece7 78%)"}}>
      <Robot f={modelFrame}/>
    </div>}
    {context>0&&<div style={{...position(1137,144,665,809),opacity:context,overflow:"hidden",borderRadius:12}}>
      <div style={{position:"absolute",left:0,top:-lerp(0,132,inspect),width:665,
        transform:"scale(1.57)",transformOrigin:"0 0"}}>
        <NativeCrop image="m01" box={panelArea} style={{left:0,top:0}}/>
      </div>
    </div>}
    {controlsFocus>0&&<div style={{...position(1190,660,controlsBox.width*controlScale,controlsBox.height*controlScale),
      borderRadius:12,overflow:"hidden",opacity:controlsFocus,boxShadow:"0 16px 40px #46372116"}}>
      <NativeCrop image={partSource} box={controlsBox} style={{left:0,top:0,transform:`scale(${controlScale})`,transformOrigin:"0 0"}}/>
      <Cursor x={cursorX} y={cursorY} press={controlClick}
        opacity={ease(f,420,428)*(1-ease(f,521,532))}/>
    </div>}
    {f>=94&&f<168&&<Cursor x={lerp(510,hover.x,cursorIn)} y={lerp(316,hover.y,cursorIn)} press={click} opacity={1-ease(f,160,168)}/>}
    {f<54&&<Img src={staticFile("robot-status-phase-v1/live-map.png")} style={{...position(0,0,1920,1080),opacity:mapFade}}/>}
    {f>=14&&f<78&&<div style={{...position(lerp(mapLabelX-48,page.x+row.x*page.scale+41,handoff),lerp(mapLabelY-41,page.y+row.y*page.scale+9,handoff),96,42),
      background:"#ffe7d8",border:"1px solid #ec985f",borderRadius:7,display:"grid",placeItems:"center",
      fontSize:23,fontWeight:850,color:orange,opacity:ease(f,14,19)*(1-ease(f,66,78))}}>M01</div>}
    {voice&&<div style={{position:"absolute",bottom:25,alignSelf:"center",background:"#231e1bea",color:"white",
      borderRadius:8,padding:"7px 17px",fontSize:30,fontWeight:650,opacity:ease(f,voice.from,voice.from+3)*(1-ease(f,voice.to-3,voice.to))}}>{voice.text}</div>}
    <Audio src={asset("voice.wav")}/><Audio src={asset("score.wav")}/>
  </AbsoluteFill>;
};
