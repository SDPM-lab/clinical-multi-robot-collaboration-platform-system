import {AbsoluteFill,Audio,Img,staticFile,useCurrentFrame} from "remotion";
import {Cursor,FleetScroll,Robot} from "./RobotStatusPhaseV2";
import capture from "./robot-status-phase-v2-capture.json";
import fleet from "./live-map-phase-v3-1-capture.json";
import captions from "./robot-status-phase-v7-captions.json";

const paper="#faf7f3",ink="#27211d",orange="#c54d18";
const native=(name:string)=>staticFile("robot-status-phase-v2/"+name+".png");
const sound=(name:string)=>staticFile("robot-status-phase-v7/"+name+".wav");
const unit=(f:number,a:number,b:number)=>Math.max(0,Math.min(1,(f-a)/(b-a)));
const ease=(f:number,a:number,b:number)=>{const t=unit(f,a,b);return t*t*(3-2*t);};
const mix=(a:number,b:number,t:number)=>a+(b-a)*t;
const {m01,maxScroll}=capture;
const marker=fleet.frames[fleet.frames.length-1].fleet[2].point;
const mapX=78+marker[0]*.917-145;
const mapY=194+(marker[1]-108)*.917-43;
const scale=1.30, pageX=78,pageY=-205;

export function Battery({f}:{f:number}){
  const p=ease(f,184,211);
  return <svg width="146" height="146" viewBox="0 0 146 146" aria-label="82 percent">
    <defs><clipPath id="v7-battery-circle"><circle cx="73" cy="73" r="61"/></clipPath>
      <linearGradient id="v7-liquid" x2="0" y2="1"><stop stopColor="#a4dfbb"/><stop offset="1" stopColor="#63c58e"/></linearGradient></defs>
    <circle cx="73" cy="73" r="68" fill="#e3f3e8"/>
    <circle cx="73" cy="73" r="62" fill="#f0faf3"/>
    <rect x="11" y={135-124*.82*p} width="124" height="124" fill="url(#v7-liquid)" clipPath="url(#v7-battery-circle)"/>
    <circle cx="73" cy="73" r="62" fill="none" stroke="#37a46d" strokeWidth="3"/>
    <text x="73" y="86" textAnchor="middle" fontSize="37" fill={ink}>{Math.round(82*p)}<tspan fontSize="17">%</tspan></text>
  </svg>;
}

export function Temperature({f}:{f:number}){
  const p=ease(f,193,218), angle=(135+36*p*2.7)*Math.PI/180;
  return <svg width="146" height="146" viewBox="0 0 160 160" aria-label="36 degrees Celsius">
    <defs><linearGradient id="v7-heat"><stop stopColor="#a8ddeb"/><stop offset=".5" stopColor="#ebacc6"/><stop offset="1" stopColor="#ec5551"/></linearGradient></defs>
    <circle cx="80" cy="80" r="72" fill="#fff"/>
    <path d="M32 128 A68 68 0 1 1 128 128" fill="none" stroke="url(#v7-heat)" strokeWidth="9" strokeLinecap="round"/>
    <circle cx={80+68*Math.cos(angle)} cy={80+68*Math.sin(angle)} r="5.5" fill="#534647" stroke="#fff" strokeWidth="2"/>
    <text x="80" y="94" textAnchor="middle" fontSize="41" fill={ink}>{Math.round(36*p)}<tspan fontSize="17">°C</tspan></text>
  </svg>;
}

export const RobotStatusPhaseV7=()=>{
  const f=useCurrentFrame();
  const selected=f>=102;
  const source=selected?"m01":"c01";
  const scroll=maxScroll*(1-(1-unit(f,49,76))**3);
  const wipe=ease(f,9,41);
  const handoff=ease(f,6,36);
  const reveal=ease(f,102,122);
  const reframe=ease(f,173,204);
  const caption=captions.find(c=>f>=c.from&&f<c.to);
  const targetX=pageX+(m01.x+m01.width*.58)*scale;
  const targetY=pageY+(m01.y+m01.height*.50-scroll)*scale;
  const move=ease(f,80,98), arrive=ease(f,42,49);
  const cursorX=mix(mix(624,450,arrive),targetX,move);
  const cursorY=mix(mix(388,433,arrive),targetY,move);
  const press=ease(f,100,102)*(1-ease(f,102,107));
  const labelX=pageX+(m01.x+77)*scale;
  const labelY=pageY+(m01.y+20)*scale;
  const title=f<102?"EXPLORE YOUR ROBOT FLEET.":f<177?"YOUR ROBOT. IN FOCUS.":"ROBOT STATUS AT A GLANCE.";
  const mapMask=f<42?`ellipse(${mix(0,2350,wipe)}px ${mix(0,1550,wipe)}px at ${mix(mapX,labelX,handoff)}px ${mix(mapY,147+labelY,handoff)}px)`:undefined;
  const panelBoxes=[
    {x:1163,y:174,w:307,h:246,start:178,end:196},
    {x:1484,y:174,w:307,h:246,start:187,end:205},
    {x:1163,y:435,w:628,h:305,start:195,end:215},
  ];

  return <AbsoluteFill style={{background:paper,color:ink,overflow:"hidden",fontFamily:"Inter,Arial,'Noto Sans CJK TC',sans-serif"}}>
    {f<42&&<Img src={staticFile("robot-status-phase-v1/live-map.png")}
      style={{position:"absolute",inset:0,width:1920,height:1080}}/>}
    {f<123&&<div style={{position:"absolute",inset:0,clipPath:mapMask,background:paper,
      opacity:1-reveal,pointerEvents:"none"}}>
      <div style={{position:"absolute",left:0,right:0,top:147,bottom:92,overflow:"hidden",borderRadius:12}}>
        <div style={{position:"absolute",left:pageX,top:pageY,width:1600,height:820,transform:`scale(${scale})`,transformOrigin:"0 0"}}>
          <Img src={native(source)} style={{position:"absolute",inset:0,width:1600,height:820}}/>
          {f>=49&&<FleetScroll f={f} source={source} scroll={scroll} hover={ease(f,95,101)*(1-ease(f,102,106))}/>}
        </div>
      </div>
    </div>}
    <div style={{position:"absolute",inset:0,clipPath:mapMask,pointerEvents:"none"}}>
    <div style={{position:"absolute",left:110,top:39,display:"flex",alignItems:"center",gap:12,fontSize:28,fontWeight:800}}>
      <Img src={staticFile("dashboard-v2/brand-mark.svg")} style={{width:41,height:29}}/><span>Medi<span style={{color:orange}}>Sync</span></span>
    </div>
    <div style={{position:"absolute",left:110,top:88,fontSize:42,fontWeight:850,letterSpacing:-1.2,opacity:ease(f,20,41)}}>{title}</div>
    </div>
    {f>=99&&<div style={{position:"absolute",left:mix(335,52,reframe),top:mix(153,174,reframe),
      width:mix(1340,1050,reframe),height:mix(798,744,reframe),opacity:reveal}}>
      <Robot f={mix(132,205,ease(f,108,166))} showcase/>
    </div>}
    {f>=177&&<span style={{position:"absolute",right:129,top:50,color:"#69594e",fontSize:16,fontWeight:650}}>Demo Telemetry</span>}
    {panelBoxes.map((b,i)=>{
      if(f<=b.start)return null;
      const t=ease(f,b.start,b.end);
      return <div key={i} style={{position:"absolute",left:mix(1098,b.x,t),top:mix(415,b.y,t),
        width:b.w,height:b.h,borderRadius:17,padding:22,boxSizing:"border-box",overflow:"hidden",
        background:["#f1f9f4","#fff9f7","#fff1c9"][i],border:"1px solid #e8dcd1",
        clipPath:`inset(0 ${(1-t)*100}% ${i===2?(1-t)*42:0}% 0 round 17px)`,opacity:t}}>
        <div style={{fontSize:21,fontWeight:730}}>{["Battery","Temperature","Robot information"][i]}</div>
        {i<2?<div style={{display:"grid",placeItems:"center",height:172}}>{i===0?<Battery f={f}/>:<Temperature f={f}/>}</div>:
          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:"18px 26px",marginTop:22,borderTop:"1px solid #dfcfaa",paddingTop:19}}>
            {[["Robot ID","M01"],["Operational status","Idle"],["Connection","Connected"],["Current location","Ward A"]].map(([label,value])=>
              <div key={label}><span style={{fontSize:16,color:"#665744"}}>{label}</span><div style={{fontSize:26,fontWeight:750,marginTop:3}}>{value}</div></div>)}
          </div>}
      </div>;
    })}
    {f>=41&&f<111&&<Cursor x={cursorX} y={147+cursorY} press={press} opacity={ease(f,41,46)*(1-ease(f,104,111))}/>}
    {f>=5&&f<42&&<div style={{position:"absolute",left:mix(mapX-44,labelX-5,handoff),top:mix(mapY-23,147+labelY,handoff),
      width:89,height:37,borderRadius:8,background:"#ffe9dd",color:"#974521",display:"grid",placeItems:"center",
      fontSize:22,fontWeight:800,opacity:ease(f,5,10)*(1-ease(f,33,42))}}>M01</div>}
    {caption&&<div style={{position:"absolute",bottom:23,alignSelf:"center",background:"#231e1bea",color:"white",
      borderRadius:8,padding:"6px 16px",fontSize:29,fontWeight:650}}>{caption.text}</div>}
    <Audio src={sound("voice")}/><Audio src={sound("score")}/>
  </AbsoluteFill>;
};
