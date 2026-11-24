import { AbsoluteFill, Audio, Img, staticFile, useCurrentFrame } from "remotion";
import type { CSSProperties, ReactNode } from "react";
import capture from "./task-creation-v6-capture.json";
import route from "./task-creation-v3-route.json";
import layers from "./task-creation-v4-layers.json";
import { ScheduleTitle, ScheduleMeta, ScheduleCard, timeOrder, wideStage } from "./TaskCreationV6Schedule";
import captions from "./task-creation-v8fast-captions.json";
import baselineCaptions from "./task-creation-v4-captions.json";

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
    <div style={{clipPath:mask(ease(f,2,13))}}>Create.</div>
    <div style={{clipPath:mask(ease(f,6,18)),color:"#d85912"}}>Simply.</div>
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
  const landing=ease(f,0,13);
  const selection=f<26?"initial":f<42?"type-options":"source-fixed";
  return <>
    <Headline f={f} />
    <Crop name={selection} box={form} x={formX} y={formY} scale={formScale}
      style={{...elevation,opacity:.94+.06*landing,
        boxShadow:`0 ${mix(7,23,landing)}px ${mix(17,62,landing)}px #412f1d2a`}} />
    {f>=13&&f<49&&(f<30?
      <Cursor f={f} to={onForm(p.type)} start={13} stop={21} click={24} />:
      <Cursor f={f} from={onForm(p.type)} to={onForm(p.medicine)} start={30} stop={37} click={40} />)}
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
  const radius=1530*ease(f,60,73);
  const draw=unit(f,112,137);
  return <AbsoluteFill style={{background:stage.background,
    clipPath:f<73?`circle(${radius}px at 1340px 372px)`:undefined}}>
    <Crop name="map-clean" box={map} x={mapX} y={mapY} scale={mapScale} style={elevation}>
      <RoomPulse f={f} at={81} box={{x:1328,y:554,width:132,height:110}} />
      <RoomPulse f={f} at={108} box={{x:569,y:130,width:149,height:85}} />
      {draw>0&&<svg width={1600} height={900} style={{position:"absolute",inset:0}}>
        <path d={route.d} pathLength={1} stroke={route.color} strokeWidth={route.width}
          strokeDasharray="1 1" strokeDashoffset={1-draw} strokeLinecap="round" strokeLinejoin="round" fill="none" />
      </svg>}
      <Pin f={f} at={81} name="pin-source" box={layers.source} />
      <Pin f={f} at={108} name="pin-destination" box={layers.destination} />
    </Crop>
    {f>=74&&f<92&&<Cursor f={f} to={onMap(p.pharmacy)} start={74} stop={80} />}
    {f>=94&&f<113&&<Cursor f={f} to={onMap(p.ward)} start={94} stop={102} click={106} />}
  </AbsoluteFill>;
};

const toCenter = (pt:{x:number;y:number})=>screen(pt,form,centerX,formY,formScale);

const note="Deliver medication from Pharmacy to Ward A.\nHandle as high priority.";
const RestoredForm=({f}:{f:number})=>{
  const priority=ease(f,197,205);
  const count=Math.floor(note.length*unit(f,153,195));
  return <Crop name={f>=230&&f<240?"loading":"route"} box={form}
    x={centerX} y={formY} scale={formScale} style={elevation}>
    <div style={{position:"absolute",left:39,top:500,width:386,height:28,background:"#e4e4e4",
      borderRadius:5,display:"grid",gridTemplateColumns:"repeat(4,1fr)",isolation:"isolate"}}>
      <div style={{position:"absolute",left:96.5*(1+priority),top:0,width:96.5,height:28,
        background:"#fae9dd",borderRadius:5,zIndex:-1}} />
      {["Low","Normal","High","Emergency"].map((label,i)=><span key={label}
        style={{alignSelf:"center",textAlign:"center",fontSize:12,
          fontWeight:i===(priority<.5?1:2)?700:400,color:"#494949"}}>{label}</span>)}
    </div>
    {count>0&&<div style={{position:"absolute",left:40,top:568,width:382,height:96,
      boxSizing:"border-box",background:"#fafafa",borderRadius:6,padding:"7px 8px",fontSize:12,
      lineHeight:1.55,whiteSpace:"pre-wrap",color:"#363636"}}>
      {note.slice(0,count)}{f<199&&<span style={{color:"#e88753"}}>│</span>}
    </div>}
    {f>=226&&f<230&&<div style={{position:"absolute",left:p.create.box.x,top:p.create.box.y,
      width:p.create.box.width,height:p.create.box.height,borderRadius:6,background:"#78452426"}} />}
  </Crop>;
};

const FormAction=({f}:{f:number})=><AbsoluteFill style={{
  background:stage.background,clipPath:f<159?`inset(0 ${(1-ease(f,150,159))*47}% 0 ${(1-ease(f,150,159))*47}%)`:undefined}}>
  <RestoredForm f={f} />
  {f>=186&&f<230&&(f<208?<Cursor f={f} to={toCenter(p.high)} start={186} stop={194} click={197} />:
    <Cursor f={f} from={toCenter(p.high)} to={toCenter(p.create)} start={208} stop={222} click={226} />)}
</AbsoluteFill>;

const Bell = ({ size, angle=0 }: {size:number;angle?:number})=>
  <svg aria-hidden viewBox="0 0 24 24" width={size} height={size}
    style={{transform:`rotate(${angle}deg)`,transformOrigin:"50% 50%",flexShrink:0}}
    fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
    <path d="M10.3 21a2 2 0 0 0 3.4 0M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" />
  </svg>;

const Notification = ({f}:{f:number})=>{
  const show=ease(f,240,245);
  const ring=f<246?0:f<250?mix(0,-12,ease(f,246,250)):
    f<254?mix(-12,11,ease(f,250,254)):mix(11,0,ease(f,254,260));
  const morph=ease(f,260,272);
  return <>
    <AbsoluteFill style={{opacity:1-.18*show}}><RestoredForm f={f}/></AbsoluteFill>
    <div style={{position:"absolute",left:mix(878,490,morph),top:mix(435,458,morph),
      width:mix(164,940,morph),height:mix(164,102,morph),borderRadius:mix(82,17,morph),
      border:`1px solid ${f<260?"#f6d9c5":"#b5d9c1"}`,background:f<260?"#fff9f2":"#eaf7ee",
      boxShadow:"0 16px 47px #32443a22",opacity:show,overflow:"hidden"}}>
      <div style={{position:"absolute",left:mix(82,47,morph),top:"50%",transform:"translate(-50%,-50%)",
        color:`color-mix(in srgb, #dc651f ${(1-morph)*100}%, #387257)`}}>
        {f<268?<Bell size={mix(82,34,morph)} angle={ring}/>:
          <svg viewBox="0 0 24 24" width={34} height={34} fill="none" stroke="#2b694b" strokeWidth={1.8}
            style={{opacity:ease(f,267,273)}}><circle cx={12} cy={12} r={9}/><path d="m8 12 2.4 2.5 5.6-5.8" strokeLinecap="round" strokeLinejoin="round"/></svg>}
      </div>
      <div style={{position:"absolute",top:0,bottom:0,left:92,right:48,display:"flex",alignItems:"center",
        color:"#265d40",fontSize:34,fontWeight:650,whiteSpace:"nowrap",
        clipPath:`inset(0 ${(1-ease(f,261,272))*100}% 0 0)`}}>
        <span>Created <strong>{capture.task.taskCode}</strong> “Medication delivery”</span>
      </div>
      {f>=269&&<div style={{position:"absolute",right:25,top:29,color:"#537866",fontSize:31,opacity:ease(f,269,275)}}>×</div>}
    </div>
  </>;
};

const beforeOrder=timeOrder(false);
const afterOrder=timeOrder(true);

const Schedule=({f}:{f:number})=>{
  const label=ease(f,302,316);
  const editing=f>=340&&f<390;
  const saved=f>=390;
  const confirming=f>=363&&f<390;
  const expansion=ease(f,338,347)*(1-ease(f,390,395));
  const slot=ease(f,396,407);
  const split=ease(f,391,396)*(1-ease(f,407,412));
  const draft=f>=355?"15:05":"14:20";
  const editButton={x:1599,y:195}, timeField={x:545,y:560}, saveButton={x:768,y:560};
  const cue=f<340?338:f<351?348:f<363?361:388;
  const target=f<340?editButton:f<351?timeField:f<363?saveButton:screen(p.confirm,dialog,490,299,1.95);
  const from=f<340||f>=363?undefined:f<351?editButton:timeField;
  return <AbsoluteFill style={{...wideStage,opacity:ease(f,299,306)}}>
    <ScheduleTitle x={mix(530,300,label)} y={mix(420,105,label)} size={mix(96,41,label)}
      mask={(1-ease(f,300,308))*100} />
    {f>=307&&<ScheduleMeta editing={editing} opacity={ease(f,307,318)}/>}
    {beforeOrder.map((row,i)=>{
      const hero=row.code==="T0002";
      const crosses=row.code==="T0171";
      const index=mix(i,afterOrder.findIndex(item=>item.code===row.code),slot);
      const land=ease(f,308+i*3,319+i*3);
      const separate=hero||crosses?split:0;
      const focus=hero?ease(f,330,336):0;
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
      opacity:ease(f,390,396)}}>Task changes saved</div>}
    {confirming&&<AbsoluteFill style={{background:"#302b252c",opacity:ease(f,362,368)}}>
      <Crop name="confirm" box={dialog} x={490} y={299} scale={1.95} style={elevation} />
    </AbsoluteFill>}
    {f>=332&&f<390&&(f<363||f>=378)&&<Cursor f={f} from={from} to={target} start={cue-8} stop={cue-2} click={cue}/>}
  </AbsoluteFill>;
};

// The reference version retains the longer reading beats of V7. Only the
// motion between authored cue points is interpolated; input remains continuous.
export const baselineMarks = [[0,0],[90,60],[210,150],[300,240],[390,300],[585,420]] as const;
const baselineFrame=(frame:number)=>{
  for(let i=1;i<baselineMarks.length;i++){
    const [left,from]=baselineMarks[i-1];
    const [right,to]=baselineMarks[i];
    if(frame<right)return mix(from,to,unit(frame,left,right));
  }
  return 419;
};

export type TaskCreationV8Props={reference?:boolean};
export const TaskCreationPrototypeV8Fast=({reference=false}:TaskCreationV8Props)=>{
  const global=useCurrentFrame();
  const f=reference?baselineFrame(global):global;
  const line=(reference?baselineCaptions:captions).find(c=>global>=c.from&&global<c.to);
  return <AbsoluteFill style={stage}>
    {f<73&&<Opening f={f}/>}
    {f>=60&&f<159&&<MapStage f={Math.min(f,149)}/>}
    {f>=150&&f<240&&<FormAction f={f}/>}
    {f>=240&&f<306&&<Notification f={f}/>}
    {f>=300&&<Schedule f={f}/>}
    {line&&<div style={{position:"absolute",bottom:27,left:0,right:0,textAlign:"center",fontSize:29,fontWeight:700,
      opacity:ease(global,line.from,line.from+3)*(1-ease(global,line.to-3,line.to))}}>
      <span style={{background:"#241e1bed",color:"white",borderRadius:7,padding:"6px 17px"}}>{line.text}</span>
    </div>}
    <Audio src={staticFile(reference?"task-creation-v8fast/reference-score.wav":"task-creation-v8fast/score.wav")} volume={.76}/>
    <Audio src={staticFile(reference?"task-creation-v4/voice.wav":"task-creation-v8fast/voice.wav")} volume={.94}/>
  </AbsoluteFill>;
};
