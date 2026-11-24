import { AbsoluteFill, Audio, Img, staticFile, useCurrentFrame } from "remotion";
import type { CSSProperties, ReactNode } from "react";
import capture from "./task-creation-v4-capture.json";
import route from "./task-creation-v3-route.json";
import layers from "./task-creation-v4-layers.json";
import captions from "./task-creation-v4-captions.json";

const p = capture.points;
const take = (name: string) => staticFile(`task-creation-v4/${name}.png`);
const oldTake = (name: string) => staticFile(`task-creation/${name}.png`);
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

const Headline = ({ f, schedule = false }: { f: number; schedule?: boolean }) => (
  <div style={{position:"absolute",left:schedule?136:160,top:schedule?334:355,
    fontSize:schedule?89:125,fontWeight:750,letterSpacing:"-.045em",lineHeight:1.04}}>
    <div style={{clipPath:mask(ease(f,3,18))}}>{schedule?"Schedule":"Create."}</div>
    <div style={{clipPath:mask(ease(f,10,26)),color:"#d85912"}}>{schedule?"with flexibility.":"Simply."}</div>
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
    transformOrigin:"0 0",transform:`scale(${1-.14*press})`,filter:"drop-shadow(0 1px 1px #0008)"}}>
    <path d="M1 1v19l5.3-4.6 4.1 8.3 3.8-1.8-4-8.1H18z" fill="#191817" stroke="white" strokeWidth="1.4" />
  </svg>;
};

const screen = (point: {x:number;y:number}, box: Box, x: number, y: number, s: number) =>
  ({x:x+(point.x-box.x)*s,y:y+(point.y-box.y)*s});
const onForm = (pt: {x:number;y:number})=>screen(pt,form,formX,formY,formScale);
const onMap = (pt: {x:number;y:number})=>screen(pt,map,mapX,mapY,mapScale);

const Opening = ({f}:{f:number})=>{
  const landing=ease(f,0,23);
  const selection=f<41?"initial":f<66?"type-options":"source-fixed";
  return <>
    <Headline f={f} />
    <Crop name={selection} box={form} x={formX} y={formY} scale={formScale}
      style={{...elevation,transformOrigin:"50% 63%",transform:`perspective(1800px) rotateY(${-13*(1-landing)}deg)
      rotateX(${5*(1-landing)}deg) translateZ(${-55*(1-landing)}px)`}} />
    {f>=26&&f<73&&(f<47?
      <Cursor f={f} to={onForm(p.type)} start={26} stop={35} click={39} />:
      <Cursor f={f} from={onForm(p.type)} to={onForm(p.medicine)} start={47} stop={59} click={64} />)}
  </>;
};

const Pin = ({ f, at, name, box }: {f:number;at:number;name:string;box:Box})=>{
  if(f<at)return null;
  const raise=-10*ease(f,at,at+4)*(1-ease(f,at+4,at+14));
  const drop=-16*(1-ease(f,at,at+4));
  return <Img src={take(name)} style={{position:"absolute",left:box.x,top:box.y,width:box.width,height:box.height,
    transformOrigin:"50% 68%",transform:`translateY(${raise+drop}px) scale(${.94+.06*ease(f,at,at+10)})`}} />;
};

const MapStage = ({f}:{f:number})=>{
  const settle=ease(f,90,115);
  const draw=ease(f,160,199);
  return <>
    <div style={{position:"absolute",top:28,left:108,fontSize:26,fontWeight:700,letterSpacing:"-.025em"}}>
      {f<126?"Floor 1":f<154?"Pharmacy · Fixed Source":"Pharmacy → Ward A"}
    </div>
    <div style={{position:"absolute",inset:0,perspective:1700,
      clipPath:`inset(0 ${16*(1-settle)}% 0 ${16*(1-settle)}%)`}}>
      <div style={{position:"absolute",inset:0,transformOrigin:"50% 66%",
        transform:`rotateX(${-13*(1-settle)}deg) translateY(${82*(1-settle)}px)`}}>
        <Crop name="map-clean" box={map} x={mapX} y={mapY} scale={mapScale} style={elevation}>
          {draw>0&&<svg width={1600} height={900} style={{position:"absolute",inset:0}}>
            <path d={route.d} pathLength={1} stroke={route.color} strokeWidth={route.width}
              strokeDasharray="1 1" strokeDashoffset={1-draw} strokeLinecap="round" strokeLinejoin="round" fill="none" />
          </svg>}
          <Pin f={f} at={126} name="pin-source" box={layers.source} />
          <Pin f={f} at={154} name="pin-destination" box={layers.destination} />
        </Crop>
      </div>
    </div>
    {f>=119&&f<140&&<Cursor f={f} to={onMap(p.pharmacy)} start={119} stop={125} />}
    {f>=143&&f<162&&<Cursor f={f} to={onMap({x:p.ward.x,y:p.ward.y})} start={143} stop={149} click={152} />}
  </>;
};

const FormAction = ({f}:{f:number})=>{
  const stageName=f<241?"route":f<286?"priority":"loading";
  const focus=ease(f,217,231)*(1-ease(f,237,251));
  const pressed=ease(f,281,284)*(1-ease(f,284,288));
  return <>
    <Headline f={60} />
    <Crop name={stageName} box={form} x={formX} y={formY} scale={formScale} style={elevation}>
      {f<241&&f>=233&&<Crop name="priority" box={{x:39,y:499,width:386,height:30}} x={39} y={499}
        scale={1} style={{clipPath:`inset(0 0 0 ${(1-ease(f,233,241))*100}%)`}} />}
      {focus>0&&<div style={{position:"absolute",left:39,top:499,width:386,height:29,borderRadius:7,
        outline:`2px solid rgba(230,121,56,${.46*focus})`,boxShadow:`0 0 13px rgba(230,121,56,${.21*focus})`}} />}
      {pressed>0&&<div style={{position:"absolute",left:p.create.box.x,top:p.create.box.y,width:p.create.box.width,
        height:p.create.box.height,borderRadius:5,background:`rgba(56,29,11,${.19*pressed})`}} />}
    </Crop>
    {f>=217&&f<288&&(f<250?<Cursor f={f} to={onForm(p.high)} start={217} stop={228} click={233} />:
      <Cursor f={f} from={onForm(p.high)} to={onForm(p.create)} start={250} stop={276} click={283} />)}
  </>;
};

const Notification = ({f}:{f:number})=>{
  const depth=ease(f,300,321);
  const pop=1+.025*ease(f,310,315)*(1-ease(f,315,325));
  return <>
    <Headline f={60} />
    <Crop name="success" box={form} x={formX} y={formY} scale={formScale}
      style={{...elevation,filter:`brightness(${1-.08*depth})`}} />
    <Img src={oldTake("v2-toast")} style={{position:"absolute",left:mix(1355,609,depth),top:mix(126,424,depth),
      width:mix(455,1164,depth),borderRadius:18,boxShadow:`0 ${mix(5,27,depth)}px ${mix(12,60,depth)}px #30463440`,
      transform:`scale(${pop})`,transformOrigin:"76% 40%"}} />
  </>;
};

const Schedule = ({f}:{f:number})=>{
  const confirming=f>=460&&f<482;
  const saved=f>=482;
  const name=f>=492?"saved":saved?"saved-edit":f>=448?"new-time":f>=427?"edit":"schedule";
  const schedulePoint=(pt:{x:number;y:number})=>onForm(pt);
  const target=f<417?p.task:f<427?p.edit:f<448?p.time:f<460?p.save:p.confirm;
  const click=f<417?415:f<427?425:f<448?439:f<460?458:480;
  const end=f<417?408:click-3;
  const select=ease(f,409,416)*(1-ease(f,425,429));
  return <>
    <Headline f={f-375} schedule />
    <Crop name={name} box={form} x={formX} y={formY} scale={formScale} style={elevation}>
      {f<410&&p.rows.map((row,i)=>{
        if(!row)return null;
        const embed=ease(f,375+i*3,386+i*3);
        if(embed===1)return null;
        return <div key={row.y}>
          <div style={{position:"absolute",left:row.x,top:row.y,width:row.width,height:row.height,background:"#f3f5f6"}} />
          <Crop name="schedule" box={row} x={row.x} y={row.y} scale={1}
            style={{clipPath:mask(embed),transformOrigin:"50% 100%",transform:
              `perspective(560px) rotateX(${-14*(1-embed)}deg) translateY(${-7*(1-embed)}px)`}} />
        </div>;
      })}
      {select>0&&<div style={{position:"absolute",left:p.task.box.x,top:p.task.box.y,
        width:p.task.box.width,height:p.task.box.height,borderRadius:8,
        boxShadow:`inset 0 0 0 2px rgba(231,117,57,${.64*select})`}} />}
    </Crop>
    {confirming&&<>
      <AbsoluteFill style={{background:"#302b2539"}} />
      <Crop name="confirm" box={dialog} x={490} y={299} scale={1.95} style={elevation} />
    </>}
    {f>=486&&f<495&&<Cursor f={f} to={onForm(p.edit)} start={486} stop={489} click={490} />}
    {f>=395&&f<483&&<Cursor f={f}
      to={confirming?screen(target,dialog,490,299,1.95):schedulePoint(target)}
      start={f<417?395:end-8} stop={end} click={click} />}
  </>;
};

const SharedLocation = ({f}:{f:number})=>{
  const t=ease(f,205,221);
  const a=ease(f,201,205)*(1-ease(f,218,224));
  return <>{[["Pharmacy",p.pharmacy,{x:1100,y:370}],["Ward A",p.ward,{x:1368,y:370}]].map(([label,pos,dest])=>{
    const src=onMap(pos as {x:number;y:number});
    const end=dest as {x:number;y:number};
    return <div key={label as string} style={{position:"absolute",left:mix(src.x,end.x,t),top:mix(src.y,end.y,t),
      background:"#fff3e7",color:"#773b20",borderRadius:7,padding:"6px 10px",opacity:a,fontSize:20,fontWeight:700}}>
      {label as string}
    </div>;
  })}</>;
};

const SharedId = ({f}:{f:number})=>{
  const t=ease(f,368,393);
  const target=onForm(p.taskCode??p.task);
  return <div style={{position:"absolute",left:mix(922,target.x,t),top:mix(518,target.y,t),
    color:"#7d452d",background:"#fbeee2",fontWeight:700,fontSize:mix(32,15,t),borderRadius:6,padding:"3px 7px",
    opacity:ease(f,365,371)*(1-ease(f,392,399))}}>{capture.task.taskCode}</div>;
};

export type TaskCreationV4Props = {voiceover?: string};
export const TaskCreationPrototypeV4 = ({voiceover}:TaskCreationV4Props)=>{
  const f=useCurrentFrame();
  const caption=captions.find(line=>f>=line.from&&f<line.to);
  return <AbsoluteFill style={stage}>
    {f<90?<Opening f={f}/>:f<210?<MapStage f={f}/>:f<300?<FormAction f={f}/>:f<375?<Notification f={f}/>:<Schedule f={f}/>}
    {f>=201&&f<224&&<SharedLocation f={f} />}
    {f>=365&&f<399&&<SharedId f={f} />}
    {caption&&<div style={{position:"absolute",bottom:27,left:0,right:0,textAlign:"center",fontSize:30,fontWeight:700,
      opacity:ease(f,caption.from,caption.from+4)*(1-ease(f,caption.to-4,caption.to))}}>
      <span style={{background:"#241e1bed",color:"white",borderRadius:7,padding:"6px 17px"}}>{caption.text}</span>
    </div>}
    <Audio src={staticFile("task-creation-v4/score.wav")} volume={voiceover ? .79 : 1}/>
    {voiceover&&<Audio src={staticFile(voiceover)} volume={.94}/>}
  </AbsoluteFill>;
};
