import {AbsoluteFill, Audio, Easing, Freeze, Img, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame} from "remotion";
import captions from "./live-map-phase-v3-2-captions.json";
import fleetCapture from "./live-map-phase-v3-1-capture.json";
import capture from "./live-map-phase-v3-capture.json";

const orange="#d94f1b";
const ink="#221e1c";
const muted="#675b53";
const paper="#fbf8f4";
const line="#e6d7cd";
const asset=(name:string)=>staticFile(`live-map-phase-v3/${name}`);
const refined=(name:string)=>staticFile(`live-map-phase-v3-1/${name}`);
const ease=(f:number,a:number,b:number)=>interpolate(f,[a,b],[0,1],{
  extrapolateLeft:"clamp",extrapolateRight:"clamp",easing:Easing.bezier(.35,0,.2,1)});
const mix=(a:number,b:number,t:number)=>a+(b-a)*t;

const clamp=(x:number,a:number,b:number)=>Math.min(b,Math.max(a,x));


const modes=["Third Person","First Person","Local Follow"];
const smooth=(f:number,a:number,b:number)=>{
  const p=clamp((f-a)/(b-a),0,1);
  return p*p*(3-2*p);
};
const codes=["C01","C02","M01","M02","W01","W02","W03"];
const positions=[[-99,23],[-113,18],[-145,-16],[158,-23],[105,-52],[151,31],[192,-5]];
function Tag({x,y,label,status,statusOpacity=1,active,scale=1}: {x:number;y:number;label:string;status?:string;statusOpacity?:number;active?:boolean;scale?:number}) {
  return <div style={{position:"absolute",left:x,top:y,transform:`translate(-50%,-100%) scale(${scale})`,whiteSpace:"nowrap",
    padding:"7px 12px",borderRadius:9,background:active?"#ffe2d2":"#fffdf8",border:`1px solid ${active?orange:line}`,
    color:ink,fontWeight:780,fontSize:22}}>
    {label}{status&&<span style={{fontSize:16,color:muted,marginLeft:8,opacity:statusOpacity}}>{status}</span>}
  </div>;
}
function Task({f,progress}: {f:number;progress:number}) {
  const active=progress>=1?2:progress>0?1:0;
  return <div style={{position:"absolute",right:100,top:234,width:557,
    background:"#fffcf8",border:`1px solid ${line}`,borderRadius:15,padding:"22px 23px",
    clipPath:`inset(0 ${100*(1-ease(f,67,87))}% 0 0)`,opacity:1-ease(f,134,151)}}>
    <div style={{display:"flex",justifyContent:"space-between",fontSize:22,fontWeight:800,color:orange}}>
      <span>T0002 · M01</span><span>{progress>0?"En route":"Executing"}</span>
    </div>
    <div style={{fontSize:38,marginTop:7,fontWeight:850}}>Medication Delivery</div>
    <div style={{fontSize:23,marginTop:5,color:muted}}>Pharmacy → Ward A</div>
    <div style={{position:"relative",marginTop:25,display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:9}}>
      <div style={{position:"absolute",left:6,right:123,top:8,height:3,background:"#ddd2c9"}}/>
      <div style={{position:"absolute",left:6,width:active===0?0:176*ease(f,96,122),top:8,height:3,background:orange}}/>
      {["Source","En route","Destination"].map((step,i)=><div key={step} style={{position:"relative",fontSize:18,fontWeight:i===active?850:650,color:i<=active?ink:muted}}>
        <div style={{width:18,height:18,borderRadius:12,marginBottom:8,background:i<active?orange:i===active?ink:"#ddd2c9",
          boxShadow:i===active?`0 0 0 3px ${orange}`:undefined}}/>{step}
      </div>)}
    </div>
  </div>;
}
export const LiveMapPhaseV3_3=()=>{
  const outputFrame=useCurrentFrame();
  const f=Math.min(outputFrame,539);
  const s=f<420?capture.frames[f]:fleetCapture.frames[f-420];
  const caption=captions.find(({from,to})=>outputFrame>=from&&outputFrame<to);
  const handoff=smooth(f,10,53);
  const shot=f<60?0:f<150?1:f<240?2:f<420?3:4;
  const mode=f<300?0:f<360?1:2;
  const thumb=smooth(f,288,300)+smooth(f,348,360);
  const cut=f<330?300:360;
  const focus=smooth(f,cut-5,cut)*(1-smooth(f,cut+3,cut+12));
  const aperture=mix(34,0,smooth(f,cut-5,cut+5));
  const title=shot===0?"FROM DECISION TO EXECUTION.":shot===1?"EVERY TASK. IN MOTION.":shot===2?"FOLLOW THE ROBOT.":shot===3?"THREE PERSPECTIVES. ONE LIVE MAP.":"ONE MAP. MULTIPLE MISSIONS.";
  const mapEstablished=483;
  const markersReady=498;
  const routesReady=531;
  const statusReveal=ease(f,routesReady,539);
  const at=(p:number[])=>[clamp(78+p[0]*.917,155,1765),clamp(194+(p[1]-108)*.917,300,895)];
  const [rx,ry]=at(s.robot);
  const [sx,sy]=at(s.source),[dx,dy]=at(s.destination);
  const ax=mix(1414,rx,handoff),ay=mix(554,ry,handoff);
  return <AbsoluteFill style={{background:paper,color:ink,fontFamily:"Inter, Arial, Noto Sans CJK TC, sans-serif"}}>
    <div style={{position:"absolute",left:76,top:48,display:"flex",gap:10,alignItems:"center",fontSize:30,fontWeight:850}}>
      <Img src={staticFile("dashboard-v2/brand-mark.svg")} style={{width:43,height:36}} alt=""/><span>Medi<span style={{color:orange}}>Sync</span></span>
    </div>
    <div style={{position:"absolute",left:77,top:114,fontSize:51,fontWeight:850,letterSpacing:-1.9,opacity:shot===0?handoff:shot===4?ease(f,mapEstablished,mapEstablished+6):1}}>{title}</div>
    <div style={{position:"absolute",left:78,top:194,width:1760,height:792,borderRadius:21,overflow:"hidden",background:"#e8ebeb",
      clipPath:`inset(${(1-handoff)*46}% ${(1-handoff)*43}% round 21px)`,opacity:handoff,border:`1px solid ${line}`}}>
      <Sequence durationInFrames={420} layout="none">
        <OffthreadVideo src={asset("map.mp4")} muted style={{width:"100%",height:"100%",objectFit:"cover"}}/>
      </Sequence>
      <Sequence from={420} durationInFrames={180} layout="none">
        <Freeze frame={119} active={outputFrame>=539}>
          <OffthreadVideo src={refined("fleet.mp4")} muted style={{position:"absolute",inset:0,width:"100%",height:"100%",objectFit:"cover"}}/>
        </Freeze>
      </Sequence>
      {shot===3&&focus>0&&<svg viewBox="0 0 1760 792" width="1760" height="792"
        style={{position:"absolute",inset:0,opacity:.72*focus,pointerEvents:"none"}}>
        <g fill="none" stroke="#fffdf7" strokeWidth="2.5" strokeLinecap="round">
          {[-1,1].flatMap(x=>[-1,1].map(y=><path key={x+":"+y}
            d={`M ${880+x*(335+aperture)} ${396+y*(210+aperture-22)} v ${22*y} h ${-22*x}`}/>))}
        </g>
      </svg>}
    </div>
    {f<54&&<div style={{position:"absolute",left:82,top:367,width:555,opacity:1-handoff,padding:"37px",background:"#2f231d",color:"white",borderRadius:17}}>
      <div style={{fontSize:69,fontWeight:850}}>Task T0002</div>
      <div style={{fontSize:33,color:"#ffba95",marginTop:15}}>Medication Delivery</div>
      <div style={{fontSize:24,marginTop:16}}>Demo assignment</div>
    </div>}
    {f<184&&<Tag x={ax} y={ay} label={f<29?"Assigned Robot M01":"M01"} scale={mix(2.1,1,handoff)} active/>}
    {f>=42&&f<147&&<>
      {f>=97&&<Tag x={sx-93} y={sy+37} label="Pharmacy"/>}
      <Tag x={dx-35} y={dy-15} label="Ward A"/>
    </>}
    {f>=61&&f<151&&<Task f={f} progress={s.progress}/>}
    {f>=146&&f<235&&<div style={{position:"absolute",right:102,top:219,background:orange,color:"white",padding:"10px 17px",
      borderRadius:9,fontSize:24,fontWeight:800,opacity:ease(f,149,161)}}>{f<166?"Follow Robot":"Following M01"}</div>}
    {shot===0&&<div style={{position:"absolute",left:106,top:220,background:paper,padding:"8px 14px",borderRadius:8,color:muted,fontSize:22,fontWeight:700,opacity:handoff}}>
      Every assignment, visible in real time.
    </div>}
    {shot===3&&<div style={{position:"absolute",right:82,top:121,width:717,height:50,
      borderRadius:13,background:"#f0e5dc",boxShadow:`0 0 0 1px ${line}`,overflow:"hidden"}}>
      <div style={{position:"absolute",inset:0,display:"grid",gridTemplateColumns:"repeat(3,minmax(0,1fr))"}}>
        {modes.map((name,i)=><div key={name} style={{display:"grid",placeItems:"center",padding:"0 7px",
          whiteSpace:"nowrap",fontSize:19,fontWeight:800,color:ink}}>0{i+1} {name.toUpperCase()}</div>)}
      </div>
      <div aria-hidden style={{position:"absolute",inset:0,
        clipPath:`inset(0 ${(2-thumb)*100/3}% 0 ${thumb*100/3}%)`,
        background:orange,display:"grid",gridTemplateColumns:"repeat(3,minmax(0,1fr))"}}>
        {modes.map((name,i)=><div key={name} style={{display:"grid",placeItems:"center",padding:"0 7px",
          whiteSpace:"nowrap",fontSize:19,fontWeight:800,color:"white"}}>0{i+1} {name.toUpperCase()}</div>)}
      </div>
    </div>}
    {shot===3&&<div style={{position:"absolute",left:105,top:220,background:paper,padding:"9px 15px",borderRadius:9,fontSize:22,fontWeight:800}}>
      0{mode+1} / {modes[mode].toUpperCase()} · Simulated view
    </div>}
    {shot===4&&<>
      <div style={{position:"absolute",left:103,top:220,background:paper,padding:"10px 16px",borderRadius:9,fontSize:24,fontWeight:700,opacity:statusReveal}}>
        Seven robots. Connected operations.
      </div>
      {f>markersReady&&<svg viewBox="0 0 1920 1080" width="1920" height="1080" style={{position:"absolute",left:0,top:0,pointerEvents:"none",clipPath:"inset(194px 82px 94px 78px round 20px)"}}>
        {fleetCapture.frames[f-420].routes.map((route,i)=>{
          const color=["#77746D","#5D9DD3","#FB9966"][i];
          const reveal=ease(f,markersReady+i*6,[517,524,routesReady][i]);
          const project=([x,y]:number[])=>[78+x*(1760/1920),194+(y-108)*(1760/1920)+[0,-6,6][i]];
          const full=route.points.map(project);
          const d=full.map(([x,y],j)=>`${j?"L":"M"}${x},${y}`).join(" ");
          let remaining=route.progress*route.lengths.reduce((a,b)=>a+b,0);
          const done=[full[0]];
          for(let j=0;j<route.lengths.length;j++){
            const length=route.lengths[j];
            const t=clamp(remaining/length,0,1);
            done.push([mix(full[j][0],full[j+1][0],t),mix(full[j][1],full[j+1][1],t)]);
            remaining-=length;
            if(t<1)break;
          }
          const completed=done.map(([x,y],j)=>`${j?"L":"M"}${x},${y}`).join(" ");
          return <g key={route.id} opacity={reveal}>
            <defs><mask id={`v33-draw-${i}`}><path d={d} fill="none" stroke="white" strokeWidth="16" pathLength="1" strokeDasharray={`${reveal} 1`}/></mask></defs>
            <g mask={`url(#v33-draw-${i})`}>
              <path d={d} stroke="#fffdf7" strokeWidth="10" fill="none" opacity=".9"/>
              <path d={d} stroke={color} strokeWidth="4" strokeDasharray="8 7" fill="none"/>
              <path d={completed} stroke={color} strokeWidth="7" strokeLinecap="round" fill="none"/>
            </g>
          </g>;
        })}
      </svg>}
      {f>mapEstablished&&s.fleet.map((bot,i)=>{
        const [x,y]=at(bot.point);
        const [ox,oy]=positions[i];
        const m01=i===2;
        const status=m01?s.progress>=1?"Arrived":"Executing":i===0||i===3?"En route":i>=4?"Charging":"Idle";
        return <div key={bot.id} style={{opacity:ease(f,mapEstablished+(i%3)*2,markersReady)}}>
          <svg width="1920" height="1080" style={{position:"absolute",left:0,top:0,pointerEvents:"none"}}>
            <path d={`M${x} ${y}L${x+ox} ${y+oy}`} stroke={m01?orange:"#8e8076"} strokeWidth={m01?3:1.5}/>
            <circle cx={x} cy={y} r={m01?7:5} fill={m01?orange:"#5e5147"}/>
          </svg>
          <Tag x={clamp(x+ox,170,1745)} y={clamp(y+oy,303,914)} label={codes[i]} status={status} statusOpacity={statusReveal} active={m01}/>
        </div>;
      })}
      <div style={{position:"absolute",left:103,bottom:119,display:"flex",gap:15,padding:"10px 14px",borderRadius:9,background:paper,
        opacity:statusReveal,fontSize:19,fontWeight:780}}>
        {["M01 Medication","M02 Specimen","C01 Waste"].map((name,i)=><span key={name} style={{borderLeft:`5px solid ${["#77746D","#5D9DD3","#FB9966"][i]}`,paddingLeft:8}}>{name}</span>)}
      </div>
      <div style={{position:"absolute",right:106,bottom:119,background:paper,border:`1px solid ${line}`,borderRadius:9,
        padding:"10px 15px",fontSize:20,fontWeight:750,opacity:statusReveal}}>7 robots · {s.progress>=1?"2 active · 1 arrived":"3 active missions"} · Simulated</div>
    </>}
    {caption&&<div style={{position:"absolute",bottom:27,alignSelf:"center",background:ink,color:"white",padding:"8px 20px",borderRadius:8,fontSize:30}}>{caption.text}</div>}
    <Audio src={staticFile("live-map-phase-v3-2/voice.wav")}/><Audio src={staticFile("live-map-phase-v3-2/score.wav")}/>
  </AbsoluteFill>;
};
