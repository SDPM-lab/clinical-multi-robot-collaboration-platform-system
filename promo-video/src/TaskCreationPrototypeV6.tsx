import { AbsoluteFill, Audio, Img, staticFile, useCurrentFrame } from "remotion";
import type { CSSProperties, ReactNode } from "react";
import capture from "./task-creation-v6-capture.json";
import route from "./task-creation-v3-route.json";
import layers from "./task-creation-v4-layers.json";
import { ScheduleStoryboard, ScheduleTitle, ScheduleMeta, ScheduleCard, timeOrder, wideStage } from "./TaskCreationV6Schedule";
import type { ScheduleKeyframe } from "./TaskCreationV6Schedule";
import captions from "./task-creation-v4-captions.json";

const p = capture.points;
const take = (name: string) => staticFile(`${name.startsWith("pin-")?"task-creation-v4":"task-creation-v6"}/${name}.png`);
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
    <div style={{clipPath:mask(ease(f,3,18))}}>Create.</div>
    <div style={{clipPath:mask(ease(f,10,26)),color:"#d85912"}}>Simply.</div>
  </div>
);

const Cursor = ({ from, to, f, start, stop, click }: {
  from?: {x:number;y:number}; to:{x:number;y:number}; f:number; start:number; stop:number; click?:number;
}) => {
  const t=ease(f,start,stop);
  const x=mix(from?.x??to.x+74,to.x,t);
  const y=mix(from?.y??to.y+38,to.y,t);
  const press=click===undefined?0:Math.max(0,1-Math.abs(f-click-2)/4);
  return <svg viewBox="0 0 24 26" width={22} height={24} style={{position:"absolute",left:x,top:y,
    transformOrigin:"0 0",transform:`scale(${1-.12*press})`}}>
    <polygon points="1,1 1,20 6,16 10,24 14,22 10,14 18,14" fill="#191817" stroke="white" strokeWidth="1.35" strokeLinejoin="round" />
  </svg>;
};

const screen = (point: {x:number;y:number}, box: Box, x: number, y: number, s: number) =>
  ({x:x+(point.x-box.x)*s,y:y+(point.y-box.y)*s});
const onForm = (pt: {x:number;y:number})=>screen(pt,form,formX,formY,formScale);
const onMap = (pt: {x:number;y:number})=>screen(pt,map,mapX,mapY,mapScale);

const Opening = ({f}:{f:number})=>{
  const landing=ease(f,0,19);
  const selection=f<41?"initial":f<66?"type-options":"source-fixed";
  return <>
    <Headline f={f} />
    <Crop name={selection} box={form} x={formX} y={formY} scale={formScale}
      style={{...elevation,opacity:.94+.06*landing,
        boxShadow:`0 ${mix(7,23,landing)}px ${mix(17,62,landing)}px #412f1d2a`}} />
    {f>=26&&f<73&&(f<47?
      <Cursor f={f} to={onForm(p.type)} start={26} stop={35} click={39} />:
      <Cursor f={f} from={onForm(p.type)} to={onForm(p.medicine)} start={47} stop={59} click={64} />)}
  </>;
};

const Pin = ({ f, at, name, box }: {f:number;at:number;name:string;box:Box})=>{
  if(f<at)return null;
  const reveal=ease(f,at,at+10);
  return <Img src={take(name)} style={{position:"absolute",left:box.x,top:box.y,
    width:box.width,height:box.height,opacity:reveal,transformOrigin:"50% 68%",
    transform:`scale(${.60+.40*reveal})`}} />;
};

const RoomPulse = ({ f, at, box }: {f:number;at:number;box:Box})=>{
  if(f<at||f>=at+18)return null;
  const pulse=ease(f,at,at+5)*(1-ease(f,at+5,at+18));
  return <div style={{position:"absolute",left:box.x,top:box.y,width:box.width,height:box.height,
    borderRadius:4,boxShadow:`inset 0 0 0 2px rgba(218,101,32,${pulse*.7})`,
    background:`rgba(255,192,102,${pulse*.13})`}} />;
};

const MapStage = ({f}:{f:number})=>{
  const radius=1530*ease(f,90,118);
  const draw=unit(f,158,199);
  return <AbsoluteFill style={{background:stage.background,
    clipPath:f<118?`circle(${radius}px at 1340px 372px)`:undefined}}>
    <Crop name="map-clean" box={map} x={mapX} y={mapY} scale={mapScale} style={elevation}>
      <RoomPulse f={f} at={126} box={{x:1328,y:554,width:132,height:110}} />
      <RoomPulse f={f} at={154} box={{x:569,y:130,width:149,height:85}} />
      {draw>0&&<svg width={1600} height={900} style={{position:"absolute",inset:0}}>
        <path d={route.d} pathLength={1} stroke={route.color} strokeWidth={route.width}
          strokeDasharray="1 1" strokeDashoffset={1-draw} strokeLinecap="round" strokeLinejoin="round" fill="none" />
      </svg>}
      <Pin f={f} at={126} name="pin-source" box={layers.source} />
      <Pin f={f} at={154} name="pin-destination" box={layers.destination} />
    </Crop>
    {f>=119&&f<139&&<Cursor f={f} to={onMap(p.pharmacy)} start={119} stop={125} />}
    {f>=142&&f<161&&<Cursor f={f} to={onMap(p.ward)} start={142} stop={149} click={152} />}
  </AbsoluteFill>;
};

const toCenter = (pt:{x:number;y:number})=>screen(pt,form,centerX,formY,formScale);

const FormAction = ({f}:{f:number})=>{
  const stageName=f<241?"route":f<286?"priority":"loading";
  const mapMatch=1-ease(f,211,222);
  const focus=ease(f,216,231)*(1-ease(f,239,252));
  const pressed=ease(f,281,284)*(1-ease(f,284,288));
  return <>
    <Crop name={stageName} box={form} x={centerX} y={formY} scale={formScale} style={elevation}>
      {f<241&&f>=233&&<Crop name="priority" box={{x:39,y:499,width:386,height:30}} x={39} y={499}
        scale={1} style={{clipPath:`inset(0 0 0 ${(1-ease(f,233,241))*100}%)`}} />}
      {mapMatch>0&&[[39,188,"#e75b50"],[237,188,"#277f9b"]].map(([left,width,color])=>
        <div key={left} style={{position:"absolute",left:Number(left),top:287,width:Number(width),height:31,
          outline:`2px solid ${color}`,borderRadius:7,opacity:mapMatch*.62}} />)}
      {focus>0&&<div style={{position:"absolute",left:39,top:499,width:386,height:29,borderRadius:7,
        outline:`2px solid rgba(230,121,56,${.46*focus})`}} />}
      {pressed>0&&<div style={{position:"absolute",left:p.create.box.x,top:p.create.box.y,width:p.create.box.width,
        height:p.create.box.height,borderRadius:5,background:`rgba(56,29,11,${.19*pressed})`}} />}
    </Crop>
    {f>=217&&f<288&&(f<250?<Cursor f={f} to={toCenter(p.high)} start={217} stop={228} click={233} />:
      <Cursor f={f} from={toCenter(p.high)} to={toCenter(p.create)} start={250} stop={276} click={283} />)}
  </>;
};

const Bell = ({ size, angle=0 }: {size:number;angle?:number})=>
  <svg aria-hidden viewBox="0 0 24 24" width={size} height={size}
    style={{transform:`rotate(${angle}deg)`,transformOrigin:"50% 50%",flexShrink:0}}
    fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
    <path d="M10.3 21a2 2 0 0 0 3.4 0M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" />
  </svg>;

const Notification = ({f}:{f:number})=>{
  const show=ease(f,300,307);
  const ring=f<307?0:f<312?mix(0,-12,ease(f,307,312)):
    f<318?mix(-12,11,ease(f,312,318)):mix(11,0,ease(f,318,326));
  const morph=ease(f,326,348);
  return <>
    <Crop name="success" box={form} x={centerX} y={formY} scale={formScale}
      style={{...elevation,opacity:1-.28*show}}/>
    <div style={{position:"absolute",left:mix(878,490,morph),top:mix(435,458,morph),
      width:mix(164,940,morph),height:mix(164,102,morph),borderRadius:mix(82,17,morph),
      border:`1px solid ${f<326?"#f6d9c5":"#b5d9c1"}`,background:f<326?"#fff9f2":"#eaf7ee",
      boxShadow:"0 16px 47px #32443a22",opacity:show,overflow:"hidden"}}>
      <div style={{position:"absolute",left:mix(82,47,morph),top:"50%",transform:"translate(-50%,-50%)",
        color:`color-mix(in srgb, #dc651f ${(1-morph)*100}%, #387257)`}}>
        {f<341?<Bell size={mix(82,34,morph)} angle={ring}/>:
          <svg viewBox="0 0 24 24" width={34} height={34} fill="none" stroke="#2b694b" strokeWidth={1.8}
            style={{opacity:ease(f,340,349)}}><circle cx={12} cy={12} r={9}/><path d="m8 12 2.4 2.5 5.6-5.8" strokeLinecap="round" strokeLinejoin="round"/></svg>}
      </div>
      <div style={{position:"absolute",top:0,bottom:0,left:92,right:48,display:"flex",alignItems:"center",
        color:"#265d40",fontSize:34,fontWeight:650,whiteSpace:"nowrap",
        clipPath:`inset(0 ${(1-ease(f,331,350))*100}% 0 0)`}}>
        <span>Created <strong>{capture.task.taskCode}</strong> “Medication delivery”</span>
      </div>
      {f>=345&&<div style={{position:"absolute",right:25,top:29,color:"#537866",fontSize:31,opacity:ease(f,345,354)}}>×</div>}
    </div>
  </>;
};

const beforeOrder=timeOrder(false);
const afterOrder=timeOrder(true);

const Schedule = ({f}:{f:number})=>{
  const label=ease(f,397,423);
  const editing=f>=467&&f<541;
  const draft=f>=491?"15:05":"14:20";
  const confirming=f>=515&&f<541;
  const saved=f>=541;
  const expansion=ease(f,465,478)*(1-ease(f,541,550));
  const slot=ease(f,553,570);
  const split=ease(f,543,553)*(1-ease(f,570,578));
  const editButton={x:1599,y:195};
  const timeField={x:550,y:559};
  const saveButton={x:768,y:560};
  const cue=f<467?465:f<491?480:f<515?513:538;
  const target=f<467?editButton:f<491?timeField:f<515?saveButton:screen(p.confirm,dialog,490,299,1.95);
  const cursorFrom=f<467||f>=515?undefined:f<491?editButton:timeField;
  return <AbsoluteFill style={wideStage}>
    <ScheduleTitle x={mix(530,300,label)} y={mix(420,105,label)} size={mix(96,41,label)}
      mask={(1-ease(f,390,402))*100} />
    {f>=410&&<ScheduleMeta editing={editing} opacity={ease(f,410,427)}/>}
    {beforeOrder.map((row,i)=>{
      const hero=row.code==="T0002";
      const crosses=row.code==="T0171";
      const targetIndex=afterOrder.findIndex(item=>item.code===row.code);
      const land=ease(f,411+i*4,429+i*4);
      const index=mix(i,targetIndex,slot);
      const separate=hero||crosses?split:0;
      const focus=hero?ease(f,450,464):0;
      const x=mix(300-focus*33*expansion,hero?980:300,separate);
      const width=mix(1320+focus*66*expansion,639,separate);
      const height=118+(hero?111*expansion:0);
      const y=242+index*141+(i>1?111*expansion:0)-32*(1-land);
      const showTime=saved?row.revised??row.start:row.start;
      return <ScheduleCard key={row.code} row={row} x={x} y={y} width={width} height={height}
        selected={hero&&focus>.2} time={showTime} opacity={land} edit={hero&&editing} draft={draft}/>;
    })}
    {saved&&<div style={{position:"absolute",left:466,top:835,color:"#265d40",background:"#eaf7ee",
      border:"1px solid #b5d9c1",borderRadius:8,padding:"10px 16px",fontSize:19,fontWeight:650,
      opacity:ease(f,541,551)}}>Task changes saved</div>}
    {confirming&&<>
      <AbsoluteFill style={{background:"#302b252c"}} />
      <Crop name="confirm" box={dialog} x={490} y={299} scale={1.95} style={elevation} />
    </>}
    {f>=456&&f<541&&<Cursor f={f} from={cursorFrom} to={target} start={cue-9} stop={cue-3} click={cue}/>}
  </AbsoluteFill>;
};

export type TaskCreationV6Props = {voiceover?: string;keyframe?:ScheduleKeyframe};
export const TaskCreationPrototypeV6 = ({voiceover,keyframe}:TaskCreationV6Props)=>{
  const f=useCurrentFrame();
  if(keyframe)return <ScheduleStoryboard phase={keyframe}/>;
  const caption=captions.find(line=>f>=line.from&&f<line.to);
  return <AbsoluteFill style={stage}>
    {f<118&&<Opening f={f}/>}
    {f>=90&&f<210&&<MapStage f={f}/>}
    {f>=210&&f<300&&<FormAction f={f}/>}
    {f>=300&&f<390&&<Notification f={f}/>}
    {f>=390&&<Schedule f={f}/>}
    {caption&&<div style={{position:"absolute",bottom:27,left:0,right:0,textAlign:"center",fontSize:30,fontWeight:700,
      opacity:ease(f,caption.from,caption.from+4)*(1-ease(f,caption.to-4,caption.to))}}>
      <span style={{background:"#241e1bed",color:"white",borderRadius:7,padding:"6px 17px"}}>{caption.text}</span>
    </div>}
    <Audio src={staticFile("task-creation-v6/score.wav")} volume={voiceover ? .79 : 1}/>
    {voiceover&&<Audio src={staticFile(voiceover)} volume={.94}/>}
  </AbsoluteFill>;
};
