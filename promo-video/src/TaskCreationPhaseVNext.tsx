import { AbsoluteFill, Audio, Img, staticFile, useCurrentFrame } from "remotion";
import type { CSSProperties, ReactNode } from "react";
import capture from "./task-creation-phase-vnext-capture.json";
import route from "./task-creation-v3-route.json";
import layers from "./task-creation-phase-vnext-layers.json";
import { ScheduleTitle, ScheduleMeta, ScheduleCard, timeOrder, wideStage } from "./TaskCreationV6Schedule";
import captions from "./task-creation-v10-captions.json";

const p = capture.points;
const take = (name: string) => staticFile(`task-creation-phase-vnext/${name}.png`);
const mix = (a: number, b: number, t: number) => a + (b - a) * t;
const unit = (f: number, a: number, b: number) => Math.max(0, Math.min(1, (f-a)/(b-a)));
const ease = (f: number, a: number, b: number) => {
  const t = unit(f, a, b);
  return t*t*t*(10+t*(-15+6*t));
};
type Box = {x: number; y: number; width: number; height: number};
const form = {x: 24, y: 100, width: 416, height: 620};
const map = {x: 483, y: 79, width: 1095, height: 618};
const dialog = {x: 560, y: 333, width: 480, height: 234};
const formX = 1060;
const formY = 88;
const formScale = 1.38;
const centerX = (1920-form.width*formScale)/2;
const mapX = 100;
const mapY = 74;
const mapScale = 1.57;

const Crop = ({ name, box, x, y, scale, style, children }: {
  name: string; box: Box; x: number; y: number; scale: number; style?: CSSProperties; children?: ReactNode;
}) => <div style={{position:"absolute",left:x,top:y,width:box.width*scale,height:box.height*scale,overflow:"hidden",...style}}>
  <div style={{position:"absolute",width:1600,height:900,left:-box.x*scale,top:-box.y*scale,
    transformOrigin:"0 0",transform:`scale(${scale})`}}>
    <Img src={take(name)} style={{position:"absolute",width:1600,height:900}} />
    {children}
  </div>
</div>;

const stage = {background:"#faf7f2",color:"#231d19",overflow:"hidden" as const,
  fontFamily:"Arial, 'Noto Sans CJK TC', sans-serif"};
const elevation = {borderRadius:17,boxShadow:"0 24px 64px #412f1d2c"};
const mask = (progress: number) => `inset(0 0 ${100*(1-progress)}% 0)`;

const Headline = ({ f }: { f: number }) => (
  <div style={{position:"absolute",left:160,top:355,
    fontSize:125,fontWeight:750,letterSpacing:"-.045em",lineHeight:1.04}}>
    <div style={{clipPath:mask(ease(f,2,13))}}>Create.</div>
    <div style={{clipPath:mask(ease(f,6,18)),color:"#d85912"}}>Simply.</div>
  </div>
);

type Point = {x:number;y:number};
type Action = Point & {start:number; arrival:number; press?:number};
const CursorTrack=({f,actions,opacity=1}:{f:number;actions:Action[];opacity?:number})=>{
  const index=actions.reduce((active,action,i)=>f>=action.start?i:active,-1);
  if(index<0)return null;
  const current=actions[index];
  const previous=actions[index-1]??{x:current.x+55,y:current.y+35};
  const t=ease(f,current.start,current.arrival);
  const curve=4*t*(1-t);
  const x=mix(previous.x,current.x,t);
  const y=mix(previous.y,current.y,t)-18*curve;
  const press=current.press===undefined?0:Math.max(0,1-Math.abs(f-current.press-1)/2);
  return <svg viewBox="0 0 24 26" width={22} height={24} style={{position:"absolute",left:x,top:y,opacity,
    transformOrigin:"0 0",transform:`scale(${1-.15*press})`}}>
    <polygon points="1,1 1,20 6,16 10,24 14,22 10,14 18,14" fill="#191817" stroke="white" strokeWidth="1.35" strokeLinejoin="round" />
  </svg>;
};

const screen = (point: Point, box: Box, x: number, y: number, s: number) =>
  ({x:x+(point.x-box.x)*s,y:y+(point.y-box.y)*s});

const dualMapScale=.97;
const dualMapX=1920-78-map.width*dualMapScale;
const dualFormX=1920-1288-form.width*1.22;

const mapBox=(f:number)=>{
  const expand=ease(f,137,154)*(1-ease(f,193,202));
  const dismiss=ease(f,202,211);
  return {x:mix(dualMapX,mapX,expand)+1220*dismiss,y:mix(230,mapY,expand),scale:mix(dualMapScale,mapScale,expand)};
};
const formBox=(f:number)=>{
  const dual=ease(f,60,86)*(1-ease(f,202,211));
  const stepAside=ease(f,137,154)*(1-ease(f,193,202));
  const centered=ease(f,202,211);
  return {x:mix(mix(formX,dualFormX,dual),centerX,centered)-640*stepAside,
    y:mix(formY,160,dual),scale:mix(formScale,1.22,dual)};
};
const actions:Action[]=[
  {...screen(p.type,form,formX,formY,formScale),start:15,arrival:22,press:26},
  {...screen(p.medicine,form,formX,formY,formScale),start:32,arrival:44,press:48},
  {...screen(p.ward,map,dualMapX,230,dualMapScale),start:109,arrival:130,press:135},
  {...screen(p.high,form,centerX,formY,formScale),start:231,arrival:241,press:245},
  {...screen(p.create,form,centerX,formY,formScale),start:257,arrival:274,press:279},
];

const Pin = ({ f, at, name, box }: {f:number;at:number;name:string;box:Box})=>{
  if(f<at)return null;
  const reveal=ease(f,at,at+10);
  return <Img src={take(name)} style={{position:"absolute",left:box.x,top:box.y,
    width:box.width,height:box.height,opacity:reveal,transformOrigin:"50% 68%",
    transform:`scale(${.60+.40*reveal})`}} />;
};

const PinPulse=({f,at,box}:{f:number;at:number;box:Box})=>{
  const p=ease(f,at,at+13);
  if(f<at||p===1)return null;
  return <div style={{position:"absolute",left:box.x+box.width/2-22,top:box.y+box.height*.63-18,
    width:44,height:36,borderRadius:"50%",background:"radial-gradient(ellipse,#ffb17568,transparent 69%)",
    transform:`scale(${1+p*.45})`,opacity:1-p,pointerEvents:"none"}} />;
};

const MapStage = ({f}:{f:number})=>{
  const {x,y,scale}=mapBox(f);
  const draw=unit(f,154,183);
  const reveal=ease(f,75,90);
  return <Crop name="map-clean" box={map} x={x} y={y} scale={scale}
    style={{...elevation,opacity:reveal,clipPath:`inset(0 0 0 ${100*(1-ease(f,75,90))}% round 17px)`}}>
    {draw>0&&<svg width={1600} height={900} style={{position:"absolute",inset:0}}>
      <path d={route.d} pathLength={1} stroke={route.color} strokeWidth={route.width}
        strokeDasharray="1 1" strokeDashoffset={1-draw} strokeLinecap="round" strokeLinejoin="round" fill="none" />
    </svg>}
    <PinPulse f={f} at={102} box={layers.source} />
    <PinPulse f={f} at={137} box={layers.destination} />
    <Pin f={f} at={63} name="pin-source" box={layers.source} />
    <Pin f={f} at={137} name="pin-destination" box={layers.destination} />
  </Crop>;
};

const note="Deliver medication from Pharmacy to Ward A.\nHandle as high priority.";
const TaskForm=({f}:{f:number})=>{
  const {x,y,scale}=formBox(f);
  const opening=ease(f,0,13);
  const selection=f<28?"initial":f<50?"type-options":f<137?"source-fixed":f>=282&&f<300?"loading":"route";
  const priority=ease(f,245,254);
  const count=Math.floor(note.length*unit(f,211,239));
  return <Crop name={selection} box={form} x={x} y={y} scale={scale}
    style={{...elevation,opacity:(.94+.06*opening)*(1-.18*ease(f,304,309))*(1-ease(f,359,365))}}>
    {((f>=22&&f<28)||(f>=274&&f<282))&&<div style={{position:"absolute",
      ...(f<28?{left:p.type.box.x,top:p.type.box.y,width:p.type.box.width,height:p.type.box.height}:
        {left:p.create.box.x,top:p.create.box.y,width:p.create.box.width,height:p.create.box.height}),
      borderRadius:6,background:f===26||f===279?"#7845242b":"#e58a4119"}}/>}
    {f>=137&&
    <div style={{position:"absolute",left:39,top:500,width:386,height:28,background:"#e4e4e4",
      borderRadius:5,display:"grid",gridTemplateColumns:"repeat(4,1fr)",isolation:"isolate"}}>
      <div style={{position:"absolute",left:96.5*(1+priority),top:0,width:96.5,height:28,
        background:`color-mix(in srgb, #fae9dd ${100*(1-priority)}%, #f5c39f)`,borderRadius:5,zIndex:-1}} />
      {["Low","Normal","High","Emergency"].map((label,i)=><span key={label}
        style={{alignSelf:"center",textAlign:"center",fontSize:12,
          fontWeight:i===(priority<.5?1:2)?700:400,color:i===2&&priority>=.5?"#783519":"#494949"}}>{label}</span>)}
    </div>}
    {count>0&&<div style={{position:"absolute",left:40,top:568,width:382,height:96,
      boxSizing:"border-box",background:"#fafafa",borderRadius:6,padding:"7px 8px",fontSize:12,
      lineHeight:1.55,whiteSpace:"pre-wrap",color:"#363636"}}>
      {note.slice(0,count)}{f<241&&<span style={{color:"#e88753"}}>│</span>}
    </div>}
  </Crop>;
};

const Bell = ({ size, angle=0 }: {size:number;angle?:number})=>
  <svg aria-hidden viewBox="0 0 24 24" width={size} height={size}
    style={{transform:`rotate(${angle}deg)`,transformOrigin:"50% 50%",flexShrink:0}}
    fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
    <path d="M10.3 21a2 2 0 0 0 3.4 0M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" />
  </svg>;

const Notification = ({f}:{f:number})=>{
  const show=ease(f,304,309);
  const ring=f<309?0:f<313?mix(0,-12,ease(f,309,313)):
    f<317?mix(-12,11,ease(f,313,317)):mix(11,0,ease(f,317,322));
  const morph=ease(f,322,334);
  return <>
    {f<359&&<div style={{position:"absolute",left:mix(878,490,morph),top:mix(435,458,morph),
      width:mix(164,940,morph),height:mix(164,102,morph),borderRadius:mix(82,17,morph),
      border:`1px solid ${f<322?"#f6d9c5":"#b5d9c1"}`,background:f<322?"#fff9f2":"#eaf7ee",
      boxShadow:"0 16px 47px #32443a22",opacity:show,overflow:"hidden"}}>
      <div style={{position:"absolute",left:mix(82,47,morph),top:"50%",transform:"translate(-50%,-50%)",
        color:`color-mix(in srgb, #dc651f ${(1-morph)*100}%, #387257)`}}>
        {f<328?<Bell size={mix(82,34,morph)} angle={ring}/>:
          <svg viewBox="0 0 24 24" width={34} height={34} fill="none" stroke="#2b694b" strokeWidth={1.8}
            style={{opacity:ease(f,327,334)}}><circle cx={12} cy={12} r={9}/><path d="m8 12 2.4 2.5 5.6-5.8" strokeLinecap="round" strokeLinejoin="round"/></svg>}
      </div>
      <div style={{position:"absolute",top:0,bottom:0,left:92,right:48,display:"flex",alignItems:"center",
        color:"#265d40",fontSize:34,fontWeight:650,whiteSpace:"nowrap",
        clipPath:`inset(0 ${(1-ease(f,323,334))*100}% 0 0)`}}>
        <span>Created <strong>{capture.task.taskCode}</strong> “Medication delivery”</span>
      </div>
      {f>=329&&<div style={{position:"absolute",right:25,top:29,color:"#537866",fontSize:31,opacity:ease(f,329,336)}}>×</div>}
    </div>}
  </>;
};

const beforeOrder=timeOrder(false);
const afterOrder=timeOrder(true);

const Schedule=({f}:{f:number})=>{
  const label=ease(f,360,370);
  const editing=f>=393&&f<456;
  const saved=f>=456;
  const confirming=f>=424&&f<462;
  const expansion=ease(f,391,400)*(1-ease(f,456,461));
  const slot=ease(f,461,473);
  const split=ease(f,456,461)*(1-ease(f,473,477));
  const draft=f>=410?"15:05":"14:20";
  const editButton={x:1599,y:195}, timeField={x:545,y:560}, saveButton={x:768,y:560};
  const confirmButton=screen(p.confirm,dialog,490,299,1.95);
  const scheduleActions:Action[]=[
    {...editButton,start:383,arrival:389,press:391},
    {...timeField,start:394,arrival:399,press:401},
    {...saveButton,start:410,arrival:420,press:422},
    {...confirmButton,start:445,arrival:452,press:454},
  ];
  return <AbsoluteFill style={{...wideStage,opacity:ease(f,359,374)}}>
    <ScheduleTitle x={300} y={105} size={41}
      mask={(1-label)*100} />
    {f>=360&&<ScheduleMeta editing={editing} opacity={ease(f,360,370)}/>}
    {beforeOrder.map((row,i)=>{
      const hero=row.code==="T0002";
      const crosses=row.code==="T0171";
      const index=mix(i,afterOrder.findIndex(item=>item.code===row.code),slot);
      const land=hero?(f>=374?1:0):ease(f,362+i*3,372+i*3);
      const separate=hero||crosses?split:0;
      const focus=hero?ease(f,379,386):0;
      return <ScheduleCard key={row.code} row={row}
        x={mix(300-focus*33*expansion,hero?980:300,separate)}
        y={242+index*141+(i>1?111*expansion:0)-20*(1-land)}
        width={mix(1320+focus*66*expansion,639,separate)}
        height={118+(hero?111*expansion:0)}
        selected={hero&&focus>.2} time={saved?row.revised??row.start:row.start}
        opacity={land} edit={hero&&editing} draft={draft}/>;
    })}
    {saved&&<div style={{position:"absolute",left:466,top:835,color:"#265d40",background:"#eaf7ee",
      border:"1px solid #b5d9c1",borderRadius:8,padding:"10px 16px",fontSize:19,fontWeight:650,
      opacity:ease(f,456,462)}}>Task changes saved</div>}
    {confirming&&<AbsoluteFill style={{background:"#302b252c",opacity:ease(f,423,430)*(1-ease(f,456,462)),transform:`translateY(${6*(1-ease(f,424,431))}px)`}}>
      <Crop name="confirm" box={dialog} x={490} y={299} scale={1.95} style={{...elevation,borderRadius:33}} />
    </AbsoluteFill>}
    {f>=385&&f<456&&<CursorTrack f={f} actions={scheduleActions}/>}
  </AbsoluteFill>;
};

const TaskAnchor=({f}:{f:number})=>{
  const t=ease(f,359,374);
  return <div style={{position:"absolute",left:mix(490,471,t),top:mix(458,383,t),
    width:mix(940,1149,t),height:mix(102,118,t),boxSizing:"border-box",borderRadius:mix(17,12,t),
    padding:`${mix(26,13,t)}px ${mix(39,28,t)}px`,
    background:`color-mix(in srgb, #eaf7ee ${(1-t)*100}%, #fcf1f0)`,
    border:"1px solid #edd6d0",borderLeft:`${mix(1,5,t)}px solid #d65b57`,
    color:"#504036",fontSize:mix(30,16,t),fontWeight:650,boxShadow:"0 8px 32px #4d382712"}}>
    <div>{capture.task.taskCode} · {t>.45?"Unassigned":"Medication delivery"}</div>
    {t>.45&&<div style={{fontSize:27,color:"#231d19",fontWeight:730,marginTop:3}}>Medication delivery</div>}
    {t>.75&&<div style={{fontSize:18,color:"#665448",marginTop:4}}>Pharmacy → Ward A</div>}
  </div>;
};

export const TaskCreationPhaseVNext=()=>{
  const f=useCurrentFrame();
  const line=captions.find(c=>f>=c.from&&f<c.to);
  return <AbsoluteFill style={stage}>
    {f<78&&<div style={{opacity:1-ease(f,60,78)}}><Headline f={f}/></div>}
    {f>=75&&f<211&&<MapStage f={f}/>}
    {f<374&&<TaskForm f={f}/>}
    {f<283&&<CursorTrack f={f} actions={actions}
      opacity={f<58?1:f<109?1-ease(f,53,65):f<231?ease(f,109,118)*(1-ease(f,137,151))* (1-ease(f,185,201)):ease(f,231,237)}/>}
    {f>=300&&f<359&&<Notification f={f}/>}
    {f>=359&&<Schedule f={f}/>}
    {f>=359&&f<374&&<TaskAnchor f={f}/>}
    {line&&<div style={{position:"absolute",bottom:27,left:0,right:0,textAlign:"center",fontSize:29,fontWeight:700,
      opacity:ease(f,line.from,line.from+3)*(1-ease(f,line.to-3,line.to))}}>
      <span style={{background:"#241e1bed",color:"white",borderRadius:7,padding:"6px 17px"}}>{line.text}</span>
    </div>}
    <Audio src={staticFile("task-creation-v10/score.wav")} volume={.76}/>
    <Audio src={staticFile("task-creation-v10/voice.wav")} volume={.94}/>
  </AbsoluteFill>;
};
