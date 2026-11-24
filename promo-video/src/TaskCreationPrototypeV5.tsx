import { AbsoluteFill, Audio, Img, staticFile, useCurrentFrame } from "remotion";
import type { CSSProperties, ReactNode } from "react";
import capture from "./task-creation-v4-capture.json";
import route from "./task-creation-v3-route.json";
import layers from "./task-creation-v4-layers.json";
import captions from "./task-creation-v4-captions.json";

const p = capture.points;
const take = (name: string) => staticFile(`task-creation-v4/${name}.png`);
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
const scheduleY = 161;
const scheduleScale = 1.36;
const scheduleX = (1920-form.width*scheduleScale)/2;
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
    transformOrigin:"0 0",transform:`scale(${1-.14*press})`,filter:"drop-shadow(0 1px 1px #0008)"}}>
    <path d="M1 1v19l5.3-4.6 4.1 8.3 3.8-1.8-4-8.1H18z" fill="#191817" stroke="white" strokeWidth="1.4" />
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
  const focus=ease(f,216,231)*(1-ease(f,239,252));
  const pressed=ease(f,281,284)*(1-ease(f,284,288));
  return <>
    <Crop name={stageName} box={form} x={centerX} y={formY} scale={formScale} style={elevation}>
      {f<241&&f>=233&&<Crop name="priority" box={{x:39,y:499,width:386,height:30}} x={39} y={499}
        scale={1} style={{clipPath:`inset(0 0 0 ${(1-ease(f,233,241))*100}%)`}} />}
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
        <Bell size={mix(82,34,morph)} angle={ring}/>
      </div>
      <div style={{position:"absolute",top:0,bottom:0,left:92,right:48,display:"flex",alignItems:"center",
        color:"#265d40",fontSize:34,fontWeight:650,whiteSpace:"nowrap",
        clipPath:`inset(0 ${(1-ease(f,331,350))*100}% 0 0)`}}>
        Created {capture.task.taskCode} “Medication delivery”
      </div>
      {f>=345&&<div style={{position:"absolute",right:25,top:29,color:"#537866",fontSize:31,opacity:ease(f,345,354)}}>×</div>}
    </div>
  </>;
};

const Schedule = ({f}:{f:number})=>{
  const confirming=f>=479&&f<501;
  const saved=f>=501;
  const name=f>=511?"saved":saved?"saved-edit":f>=467?"new-time":f>=446?"edit":"schedule";
  const placed=ease(f,394,412);
  const title=ease(f,390,401);
  const schedulePoint=(pt:{x:number;y:number})=>screen(pt,form,scheduleX,scheduleY,scheduleScale);
  const target=f<436?p.task:f<446?p.edit:f<467?p.time:f<479?p.save:p.confirm;
  const click=f<436?434:f<446?444:f<467?458:f<479?477:499;
  const end=f<436?427:click-3;
  const select=ease(f,428,435)*(1-ease(f,444,448));
  return <>
    <div style={{position:"absolute",left:0,right:0,top:mix(407,44,placed),textAlign:"center",
      fontSize:mix(86,54,placed),lineHeight:1.12,fontWeight:750,letterSpacing:"-.046em",
      clipPath:`inset(0 ${(1-title)*50}% 0 ${(1-title)*50}%)`}}>
      Schedule <span style={{color:"#d85912"}}>with flexibility.</span>
    </div>
    {f>=400&&<Crop name={name} box={form} x={scheduleX} y={scheduleY} scale={scheduleScale}
      style={{...elevation,clipPath:mask(ease(f,400,414))}}>
      {f<429&&p.rows.map((row,i)=>{
        if(!row)return null;
        const embed=ease(f,403+i*3,413+i*3);
        if(embed===1)return null;
        return <div key={row.y}>
          <div style={{position:"absolute",left:row.x,top:row.y,width:row.width,height:row.height,background:"#f3f5f6"}} />
          <Crop name="schedule" box={row} x={row.x} y={row.y} scale={1}
            style={{clipPath:mask(embed),transformOrigin:"50% 100%",transform:
              `perspective(560px) rotateX(${-12*(1-embed)}deg) translateY(${-7*(1-embed)}px)`}} />
        </div>;
      })}
      {select>0&&<div style={{position:"absolute",left:p.task.box.x,top:p.task.box.y,
        width:p.task.box.width,height:p.task.box.height,borderRadius:8,
        boxShadow:`inset 0 0 0 2px rgba(231,117,57,${.64*select})`}} />}
    </Crop>}
    {confirming&&<>
      <AbsoluteFill style={{background:"#302b252c"}} />
      <Crop name="confirm" box={dialog} x={490} y={299} scale={1.95} style={elevation} />
    </>}
    {f>=505&&f<514&&<Cursor f={f} to={schedulePoint(p.edit)} start={505} stop={508} click={509} />}
    {f>=422&&f<502&&<Cursor f={f}
      to={confirming?screen(target,dialog,490,299,1.95):schedulePoint(target)}
      start={f<436?422:end-8} stop={end} click={click} />}
  </>;
};

const SharedLocation = ({f}:{f:number})=>{
  const t=ease(f,205,221);
  const a=ease(f,201,205)*(1-ease(f,218,224));
  return <>{[["Pharmacy",p.pharmacy,{x:707,y:368}],["Ward A",p.ward,{x:983,y:368}]].map(([label,pos,dest])=>{
    const src=onMap(pos as {x:number;y:number});
    const end=dest as {x:number;y:number};
    return <div key={label as string} style={{position:"absolute",left:mix(src.x,end.x,t),top:mix(src.y,end.y,t),
      background:"#fff3e7",color:"#773b20",borderRadius:7,padding:"6px 10px",opacity:a,fontSize:20,fontWeight:700}}>
      {label as string}
    </div>;
  })}</>;
};

const SharedId = ({f}:{f:number})=>{
  const t=ease(f,385,421);
  const target=screen(p.taskCode??p.task,form,scheduleX,scheduleY,scheduleScale);
  return <div style={{position:"absolute",left:mix(713,target.x,t),top:mix(490,target.y,t),
    color:"#7d452d",background:"#fbeee2",fontWeight:700,fontSize:mix(32,15,t),borderRadius:6,padding:"3px 7px",
    opacity:ease(f,381,387)*(1-ease(f,419,427))}}>{capture.task.taskCode}</div>;
};

export type TaskCreationV5Props = {voiceover?: string};
export const TaskCreationPrototypeV5 = ({voiceover}:TaskCreationV5Props)=>{
  const f=useCurrentFrame();
  const caption=captions.find(line=>f>=line.from&&f<line.to);
  return <AbsoluteFill style={stage}>
    {f<118&&<Opening f={f}/>}
    {f>=90&&f<210&&<MapStage f={f}/>}
    {f>=210&&f<300&&<FormAction f={f}/>}
    {f>=300&&f<390&&<Notification f={f}/>}
    {f>=390&&<Schedule f={f}/>}
    {f>=201&&f<224&&<SharedLocation f={f} />}
    {f>=381&&f<427&&<SharedId f={f} />}
    {caption&&<div style={{position:"absolute",bottom:27,left:0,right:0,textAlign:"center",fontSize:30,fontWeight:700,
      opacity:ease(f,caption.from,caption.from+4)*(1-ease(f,caption.to-4,caption.to))}}>
      <span style={{background:"#241e1bed",color:"white",borderRadius:7,padding:"6px 17px"}}>{caption.text}</span>
    </div>}
    <Audio src={staticFile("task-creation-v5/score.wav")} volume={voiceover ? .79 : 1}/>
    {voiceover&&<Audio src={staticFile(voiceover)} volume={.94}/>}
  </AbsoluteFill>;
};
