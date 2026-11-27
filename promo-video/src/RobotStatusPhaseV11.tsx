import { AbsoluteFill, Audio, Easing, Freeze, Img, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame } from "remotion";
import { Cursor } from "./RobotStatusPhaseV2";
import { WorkspaceRobot } from "./RobotStatusPhaseV9";
import captions from "./robot-status-phase-v11-captions.json";

const asset = (name: string) => staticFile(`robot-status-phase-v11/${name}`);
const paper = "#faf7f2";
const ink = "#26211f";
const orange = "#b94518";
const progress = (f: number, start: number, end: number) =>
  interpolate(f,[start,end],[0,1],{easing:Easing.bezier(.35,0,.25,1),extrapolateLeft:"clamp",extrapolateRight:"clamp"});
const mix = (a: number, b: number, t: number) => a + (b-a)*t;
const fleet = { x:1130, y:104, width:520, height:842, scale:520/694 };
const atlas = [
  {id:"c01",x:441,y:502,w:139,h:39,destination:322},
  {id:"m02",x:974,y:314,w:141,h:41,destination:772},
  {id:"w01",x:1223,y:326,w:149,h:40,destination:902},
];

const Heading = ({ lines, x, y, size, f, start, opacity = 1 }: {
  lines: string[]; x: number; y: number; size: number; f: number; start: number; opacity?: number;
}) => <div style={{position:"absolute",left:x,top:y,fontSize:size,lineHeight:1.02,fontWeight:850,letterSpacing:-size*.055,opacity}}>
  {lines.map((line,i)=>{
    const t=progress(f,start+i*5,start+i*5+15);
    return <div key={line} style={{overflow:"hidden",paddingRight:12}}>
      <div style={{transform:`translateY(${(1-t)*105}%)`,color:i===1?orange:ink}}>{line}</div>
    </div>;
  })}
</div>;

export const RobotStatusPhaseV11 = () => {
  const f=useCurrentFrame();
  const mapOut=progress(f,12,53);
  const mapDetach=(i: number)=>progress(f,10+i*3,18+i*3);
  const panelIn=progress(f,34,58);
  const panelOut=progress(f,148,174);
  const settle=progress(f,146,183);
  const orbit=progress(f,153,213);
  const activate=progress(f,167,191);
  const details=progress(f,176,198);
  const tagMove=progress(f,151,181);
  const tagOpacity=progress(f,147,154)*(1-progress(f,171,185));
  const first={x:1244,y:346};
  const second={x:1244,y:624};
  const cursorIn=progress(f,61,73);
  const cursorApproach=progress(f,106,113);
  const next=progress(f,126,139);
  const mouseX=mix(mix(1055,1398,cursorIn),first.x,cursorApproach)+(second.x-first.x)*next;
  const mouseY=mix(mix(620,538,cursorIn),first.y,cursorApproach)+(second.y-first.y)*next;
  const press=[118,144].reduce((total,at)=>Math.max(total,progress(f,at-2,at)*(1-progress(f,at,at+4))),0);
  const caption=captions.find(c=>f>=c.from&&f<c.to);

  return <AbsoluteFill style={{background:paper,color:ink,fontFamily:"Inter, Arial, 'Noto Sans CJK TC', sans-serif",overflow:"hidden"}}>
    {f<54&&<>
      <svg width={0} height={0} style={{position:"absolute"}} aria-hidden>
        <defs>
          <mask id="phase5-v11-map-anchors" maskUnits="userSpaceOnUse" x="0" y="0" width="1920" height="1080">
            <rect width="1920" height="1080" fill="white"/>
            <rect x={72} y={45} width={206} height={39} fill="black" opacity={progress(f,18,25)}/>
            {atlas.map((tag,i)=><rect key={tag.id} x={tag.x} y={tag.y} width={tag.w} height={tag.h}
              rx={6} fill="black" opacity={mapDetach(i)}/>)}
          </mask>
        </defs>
      </svg>
      <Img src={staticFile("robot-status-phase-v9/phase4-final.png")} style={{
        position:"absolute",width:1920,height:1080,opacity:1-mapOut,mask:"url(#phase5-v11-map-anchors)",
      }}/>
    </>}
    <div style={{position:"absolute",top:60,left:109,display:"flex",alignItems:"center",gap:9,fontWeight:850,fontSize:28,opacity:progress(f,25,46)}}>
      <Img src={staticFile("dashboard-v2/brand-mark.svg")} style={{width:41,height:29}}/>
      <span>Medi<span style={{color:orange}}>Sync</span></span>
    </div>
    {f<168&&<Heading lines={["EVERY ROBOT.","ONE CONNECTED","VIEW."]} x={103} y={337} size={88} start={24} f={f} opacity={1-progress(f,146,167)}/>}
    {f>=146&&<Heading lines={["EVERY DETAIL. IN VIEW."]} x={109} y={132} size={73} start={154} f={f}/>}

    {f<174&&<div style={{
      position:"absolute",left:fleet.x+(1-panelIn)*24,top:fleet.y,width:fleet.width,height:fleet.height,
      opacity:panelIn*(1-panelOut),transform:`perspective(1700px) rotateY(${(1-panelIn)*-5}deg)`,
      overflow:"hidden",borderRadius:19,boxShadow:"0 22px 65px #3f30221a",
      maskImage:"linear-gradient(#000 93%, transparent)",
    }}>
      <Sequence from={15} layout="none">
        <Freeze frame={152} active={f>=167}>
        <OffthreadVideo muted src={asset("fleet.mp4")} style={{display:"block",width:fleet.width,height:1458*fleet.scale}}/>
        </Freeze>
      </Sequence>
    </div>}

    {f<59&&atlas.map((tag,i)=>{
      const t=progress(f,18+i*3,46+i*3);
      const opacity=mapDetach(i)*(1-progress(f,40+i*2,56+i));
      return <Img key={tag.id} src={asset(`${tag.id}-map.png`)} style={{position:"absolute",
        left:mix(tag.x,1218,t),top:mix(tag.y,tag.destination,t),width:tag.w,height:tag.h,
        opacity,borderRadius:7,
      }}/>;
    })}

    <div style={{position:"absolute",inset:0,opacity:progress(f,147,168),
      transformOrigin:"0 0",transform:`translate(${mix(260,25,settle)}px, ${mix(85,44,settle)}px) scale(${mix(.91,1.02,settle)})`}}>
      <WorkspaceRobot pose={132+orbit*72}/>
    </div>

    {f>=146&&f<186&&<Img src={asset("m01-row.png")} style={{position:"absolute",
      left:mix(fleet.x+4,1400,tagMove),top:mix(542,319,tagMove),width:mix(505,379,tagMove),
      borderRadius:12,opacity:tagOpacity,
    }}/>}

    {f>=165&&<div style={{position:"absolute",left:109-30*(1-activate),top:425+18*(1-activate),width:430,height:209,
      transform:`scale(${mix(.96,1,activate)} )`,transformOrigin:"top left",opacity:activate,overflow:"hidden",borderRadius:14}}>
      <Sequence from={15} layout="none">
        <Freeze frame={194} active={f>=209}>
          <OffthreadVideo muted src={asset("telemetry.mp4")} style={{width:430,height:208.4}}/>
        </Freeze>
      </Sequence>
    </div>}

    {f>=173&&<section style={{position:"absolute",left:1423,top:314+(1-details)*18,width:390,opacity:details}}>
      <div style={{fontSize:17,color:"#6b5b51"}}>Robot ID</div>
      <div style={{display:"flex",alignItems:"baseline",gap:19,margin:"4px 0 21px"}}>
        <strong style={{fontSize:60,letterSpacing:-3,lineHeight:1}}>M01</strong>
        <span style={{fontSize:19,color:"#62554d"}}>Agibot Genie G1</span>
      </div>
      {[["Operational status","Idle"],["Connection","Connected"],["Location","Ward A"]].map(([label,value])=>
        <div key={label} style={{borderTop:"1px solid #ddcfc0",display:"flex",justifyContent:"space-between",
          alignItems:"center",padding:"16px 0",fontSize:20,color:"#5e5148"}}>
          {label}<strong style={{color:ink,fontSize:23}}>{value}</strong>
        </div>)}
    </section>}

    {f>=60&&f<156&&<Cursor x={mouseX} y={mouseY} press={press} opacity={progress(f,60,65)*(1-progress(f,147,156))}/>}
    {f>=193&&<span style={{position:"absolute",right:106,bottom:70,color:"#65594f",fontSize:15}}>Simulated telemetry</span>}
    {caption&&<div style={{position:"absolute",bottom:22,alignSelf:"center",background:"#25211e",color:"white",
      borderRadius:8,padding:"7px 16px",fontSize:28,fontWeight:650}}>{caption.text}</div>}
    <Audio src={asset("voice.wav")}/>
    <Audio src={asset("score.wav")}/>
  </AbsoluteFill>;
};
