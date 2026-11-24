import {AbsoluteFill, Audio, Img, cancelRender, staticFile, useCurrentFrame, useDelayRender} from "remotion";
import {useEffect, useLayoutEffect, useRef} from "react";
import type {CSSProperties} from "react";
import {createRobotStatusScene} from "./robotStatusScene";
import subtitles from "./robot-status-phase-v1-captions.json";
import capture from "./live-map-phase-v3-1-capture.json";

const ink="#28221f", muted="#685e58", orange="#d7531b", stroke="#e5d8cc", paper="#faf7f2";
const dir=(name:string)=>staticFile(`robot-status-phase-v1/${name}`);
const ease=(f:number,a:number,b:number)=>{
  const t=Math.max(0,Math.min(1,(f-a)/(b-a)));
  return t*t*(3-2*t);
};
const mix=(a:number,b:number,t:number)=>a+(b-a)*t;
const avatar=dir("avatar.png");
const fleet=[
  {id:"C01",type:"Cleaning",state:"Executing",location:"En route to Waste Return",battery:77,temp:34,task:"T0004"},
  {id:"C02",type:"Cleaning",state:"Idle",location:"Waiting B",battery:69,temp:32,task:"—"},
  {id:"M01",type:"Medical",state:"Idle",location:"Ward A",battery:82,temp:36,task:"—"},
  {id:"M02",type:"Medical",state:"Executing",location:"En route to Laboratory",battery:91,temp:37,task:"T0003"},
  {id:"W01",type:"Ward",state:"Charging",location:"Charging",battery:58,temp:30,task:"—"},
  {id:"W02",type:"Ward",state:"Charging",location:"Charging",battery:48,temp:31,task:"—"},
  {id:"W03",type:"Ward",state:"Charging",location:"Charging",battery:65,temp:32,task:"—"},
];
const sections=["EVERY ROBOT. ONE PLATFORM.","EXPLORE YOUR ROBOT FLEET.","STATUS AT A GLANCE.","DETAILS THAT MATTER.","INTERACTIVE 3D INSPECTION.","COMPLETE ROBOT VISIBILITY."];
const zoneLabels=["Left Arm","Right Arm","Head","Base","Whole Robot"];
const card:CSSProperties={boxSizing:"border-box",border:`1px solid ${stroke}`,borderRadius:14,background:"#fffdf9",boxShadow:"0 12px 38px #3023180c"};
const position=(left:number,top:number,width:number,height:number):CSSProperties=>({position:"absolute",left,top,width,height});
const stateColor=(state:string)=>state==="Executing"?orange:state==="Charging"?"#b98420":"#328257";

function Model({frame}:{frame:number}){
  const canvas=useRef<HTMLCanvasElement>(null);
  const scene=useRef<Awaited<ReturnType<typeof createRobotStatusScene>>|null>(null);
  const latest=useRef(frame);
  const {delayRender,continueRender}=useDelayRender();
  useLayoutEffect(()=>{latest.current=frame;scene.current?.draw(frame);},[frame]);
  useEffect(()=>{
    let disposed=false;
    const ticket=delayRender("Loading and drawing original Agibot GLB");
    createRobotStatusScene(canvas.current!,staticFile("ppo-spatial/AGIBOT_A2D.glb")).then(value=>{
      if(disposed){value.dispose();return;}
      scene.current=value;
      value.draw(latest.current);
      continueRender(ticket);
    }).catch(error=>{if(!disposed)cancelRender(error);});
    return ()=>{
      disposed=true;
      scene.current?.dispose();
      scene.current=null;
      continueRender(ticket);
    };
  },[continueRender,delayRender]);
  return <canvas ref={canvas} width={830} height={720} style={{...position(0,0,830,720),width:"100%",height:"100%"}}/>;
}

function Gauge({value,thermal}:{value:number;thermal?:boolean}){
  const color=thermal?"#de8e32":"#3db778";
  const theta=(135+value*2.7)*Math.PI/180;
  return <div style={{...card,height:222,padding:"16px 19px",background:thermal?"#fff9ee":"#f3fcf5"}}>
    <div style={{display:"flex",justifyContent:"space-between",fontSize:20,fontWeight:650}}>
      <span>{thermal?"Temperature":"Battery"}</span>
      <span style={{color,display:"grid",placeItems:"center"}}>{thermal?
        <svg width="19" height="23" viewBox="0 0 20 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M8 15V5a2 2 0 0 1 4 0v10a4 4 0 1 1-4 0Z"/><path d="M10 9v9"/></svg>:
        <svg width="19" height="23" viewBox="0 0 20 24" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="m12 2-9 12h6l-1 8 9-12h-6Z"/></svg>}</span>
    </div>
    <div style={{position:"relative",display:"grid",placeItems:"center",width:145,height:145,margin:"14px auto 0",
      borderRadius:"50%",overflow:"hidden",background:thermal?"transparent":"#e6f4ea",border:thermal?0:`3px solid ${color}`,boxSizing:"border-box"}}>
      {thermal?<svg viewBox="0 0 160 160" style={{position:"absolute",inset:0,width:"100%",height:"100%"}}>
        <defs><linearGradient id="robot-status-thermal" x2="100%" y2="0%"><stop offset="0%" stopColor="#a8ddeb"/><stop offset="45%" stopColor="#eab7cf"/><stop offset="76%" stopColor="#ed7c84"/><stop offset="100%" stopColor="#f03b38"/></linearGradient></defs>
        <path d="M32 128 A68 68 0 1 1 128 128" fill="none" stroke="#eadad7" strokeWidth="11" strokeLinecap="round"/>
        <path d="M32 128 A68 68 0 1 1 128 128" fill="none" stroke="url(#robot-status-thermal)" pathLength="100" strokeDasharray={`${value} 100`} opacity=".95" strokeWidth="6" strokeLinecap="round"/>
        <circle cx={80+68*Math.cos(theta)} cy={80+68*Math.sin(theta)} r="6.5" fill="#ad594d" stroke="#fff" strokeWidth="2"/>
      </svg>:<div style={{position:"absolute",bottom:0,left:0,right:0,height:`${value}%`,background:"linear-gradient(#8ad9a8,#62c990)"}}/>}
      <span style={{position:"relative",fontSize:45,fontWeight:800,fontVariantNumeric:"tabular-nums"}}>{Math.round(value)}<small style={{fontSize:19,marginLeft:3}}>{thermal?"°C":"%"}</small></span>
    </div>
  </div>;
}

function Cursor({x,y,pressed,opacity}:{x:number;y:number;pressed:number;opacity:number}){
  return <svg width="25" height="31" viewBox="0 0 22 27" style={{...position(x,y,25,31),opacity,
    transform:`scale(${1-pressed*.15})`,transformOrigin:"0 0",pointerEvents:"none",filter:"drop-shadow(0 2px 3px #20171066)"}}>
    <path d="M2 1 2 21 7 17 11 25 15 23 11 15 20 14Z" fill="#22201d" stroke="white" strokeWidth="1.6" strokeLinejoin="round"/>
  </svg>;
}

export const RobotStatusPhaseV1=()=>{
  const f=useCurrentFrame();
  const section=f<90?0:f<210?1:f<330?2:f<450?3:f<540?4:5;
  const mapOpacity=1-ease(f,22,65);
  const dock=ease(f,14,76);
  const activated=f>=130;
  const robot=fleet[activated?2:0];
  const scroll=165*ease(f,96,113)-94*ease(f,114,126)-71*ease(f,146,170);
  const rowHeight=mix(101,77,ease(f,540,565));
  const gaugeFocus=ease(f,209,230)*(1-ease(f,316,335));
  const infoFocus=ease(f,330,348)*(1-ease(f,438,450));
  const structFocus=ease(f,450,465)*(1-ease(f,528,548));
  const gauge=ease(f,228,267);
  const battery=activated?mix(74,robot.battery,gauge):robot.battery;
  const temperature=activated?mix(32,robot.temp,gauge):robot.temp;
  const zone=f>=521?4:f>=484?0:f>=453?2:4;
  const cue= f>=521?521:f>=484?484:f>=453?453:130;
  const down=ease(f,cue-1,cue+1)*(1-ease(f,cue+1,cue+5));
  const fleetCursor=ease(f,90,101)*(1-ease(f,140,147));
  const structureCursor=ease(f,444,453)*(1-ease(f,531,540));
  const clickTravel=ease(f,112,128);
  const pointerX=section>=4?mix(1580,1444,ease(f,445,453))+128*ease(f,513,521):mix(349,205,clickTravel);
  const pointerY=section>=4?mix(810,895,ease(f,445,453))-45*ease(f,477,484)+90*ease(f,513,521):
    mix(460,359+2*110+50-71,clickTravel);
  const last=capture.frames[capture.frames.length-1].fleet[2].point;
  const sx=78+last[0]*.917-145, sy=194+(last[1]-108)*.917-42;
  const caption=subtitles.find(line=>f>=line.from&&f<line.to);
  const details=[
    ["Robot ID",robot.id],["Floor","1F"],["Current location",robot.location],["Connection","Connected"],
    ["Manufacturer","Agibot"],["Model","Agibot Genie G1"],["Robot type",robot.type],["Assigned task",robot.task],
  ];
  return <AbsoluteFill style={{background:paper,fontFamily:"Inter, Arial, 'Noto Sans CJK TC', sans-serif",color:ink}}>
    <header style={{...position(76,45,1770,108),display:"flex",flexDirection:"column",gap:15}}>
      <div style={{display:"flex",gap:9,alignItems:"center",fontSize:27,fontWeight:800}}>
        <Img src={staticFile("dashboard-v2/brand-mark.svg")} style={{width:39,height:32}} alt=""/><span>Medi<span style={{color:orange}}>Sync</span></span>
      </div>
      <div style={{fontSize:49,letterSpacing:-1.6,fontWeight:850,lineHeight:1}}>{sections[section]}</div>
    </header>
    <div style={{...position(76,178,1768,54),...card,display:"flex",alignItems:"center",justifyContent:"space-between",padding:"0 24px",fontSize:18}}>
      <strong>MediSync</strong><div style={{display:"flex",gap:32,color:muted}}>{["Dashboard","Task Dispatch","Schedule History","Live Map","Robot Status"].map(t=>
        <span key={t} style={t==="Robot Status"?{color:orange,borderBottom:"2px solid #ee8b57",paddingBottom:5,fontWeight:750}:undefined}>{t}</span>)}</div>
      <span style={{fontWeight:700,color:muted}}>Demo Telemetry</span>
    </div>

    <aside style={{...position(76,249,355,732),...card,padding:"15px 16px",opacity:1-.22*gaugeFocus-.14*infoFocus}}>
      <div style={{border:"1px solid #ded7d0",borderRadius:9,padding:"10px 12px",color:muted,fontSize:16}}>⌕　Search robots</div>
      <div style={{display:"flex",gap:7,margin:"11px 0"}}>
        <span style={{padding:"7px 12px",borderRadius:6,background:"#ffe8d8",color:"#a4461d",fontWeight:700}}>All　7</span>
        <span style={{padding:"7px 12px",borderRadius:6,background:"#f3eee8",color:muted}}>1F　7</span>
      </div>
      <div style={{position:"absolute",left:16,right:16,top:110,height:604,overflow:"hidden",borderRadius:9}}>
        <div style={{transform:`translateY(${-scroll}px)`,marginRight:10}}>
          {fleet.map((entry,index)=>{
            const selected=entry.id===robot.id;
            const fleetBattery=entry.id==="M01"?Math.round(mix(74,entry.battery,gauge)):entry.battery;
            const hovering=index===2&&f>=124&&f<130;
            return <div key={entry.id} style={{...card,boxShadow:"none",height:rowHeight,marginBottom:9,padding:"5px 9px",
              display:"grid",gridTemplateColumns:"47px minmax(0,1fr) 42px",gap:9,alignItems:"center",
              background:selected?"#ffeadb":hovering?"#fff2e8":"#fffdf9",borderColor:selected?"#eaaa82":stroke}}>
              <Img src={avatar} style={{width:43,height:51,objectFit:"contain"}}/>
              <div style={{minWidth:0}}><strong style={{fontSize:19}}>{entry.id}</strong>
                <div style={{fontSize:15,color:stateColor(entry.state)}}>{entry.state} · F1</div>
                <div style={{fontSize:13,color:muted,whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis"}}>{entry.location}</div>
              </div>
              <span style={{textAlign:"right",fontSize:15,fontWeight:700}}>{fleetBattery}%<div style={{height:3,marginTop:5,background:"#ebe0d6"}}><div style={{height:3,width:`${fleetBattery}%`,background:"#e98049"}}/></div></span>
            </div>;
          })}
        </div>
        <div style={{position:"absolute",right:0,top:0,width:4,height:"100%",background:"#eee5df",borderRadius:3}}>
          <div style={{width:4,height:mix(474,604,ease(f,540,565)),transform:`translateY(${scroll*.78}px)`,background:"#d3ad97",borderRadius:3}}/>
        </div>
      </div>
    </aside>

    <main style={{...position(451,249,830,732),...card,overflow:"hidden",
      background:"radial-gradient(ellipse at 47% 53%,#fffdfa 5%,#eee9e2 80%)",opacity:1-.12*gaugeFocus-.12*infoFocus}}>
      <div style={{...position(0,8,830,720)}}><Model frame={f}/></div>
      <div style={{position:"absolute",left:23,top:23}}>
        <div style={{display:"flex",alignItems:"center",gap:13}}>
          <strong style={{fontSize:42}}>{robot.id}</strong><span style={{fontSize:16,color:stateColor(robot.state),fontWeight:750}}>● {robot.state}</span>
        </div>
        <div style={{color:muted,fontSize:18,marginTop:5}}>Agibot Genie G1 · {robot.location}</div>
      </div>
    </main>

    <aside style={{...position(1301,249,543,732)}}>
      <div style={{display:"grid",gap:12,gridTemplateColumns:"1fr 1fr",
        transform:`scale(${1+gaugeFocus*.038})`,transformOrigin:"bottom right",opacity:1-.14*infoFocus,
        filter:gaugeFocus>0?`drop-shadow(0 8px ${14*gaugeFocus}px #bb652424)`:undefined}}>
        <Gauge value={battery}/><Gauge value={temperature} thermal/>
      </div>
      <div style={{...card,position:"relative",height:493,marginTop:16,padding:"19px 21px",background:"#fff9ef",
        boxShadow:`0 12px 36px rgba(157,74,21,${.025+infoFocus*.10+structFocus*.12})`}}>
        <div style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
          <strong style={{fontSize:24}}>Robot Information</strong>
          <span style={{color:stateColor(robot.state),fontSize:17,fontWeight:720}}>● {robot.state}</span>
        </div>
        <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:"4px 11px",marginTop:11,borderTop:`1px solid ${stroke}`,paddingTop:8}}>
          {details.map(([label,value],i)=>{
            const highlight=ease(f,342+i*6,349+i*6)*(1-ease(f,389+i*5,407+i*5));
            return <div key={label} style={{height:52,boxSizing:"border-box",padding:"5px 7px",borderRadius:5,background:`rgba(247,167,109,${highlight*.26})`}}>
              <div style={{color:muted,fontSize:15}}>{label}</div>
              <div style={{fontWeight:700,fontSize:18,lineHeight:1.17,marginTop:3}}>{value}</div>
            </div>;
          })}
        </div>
        <div style={{position:"absolute",bottom:21,left:21,right:21,borderTop:`1px solid ${stroke}`,paddingTop:12}}>
          <div style={{fontWeight:750,fontSize:18,marginBottom:8}}>Structure</div>
          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:6}}>
            {zoneLabels.map((label,i)=><div key={label} style={{height:39,display:"grid",placeItems:"center",
              gridColumn:i===4?"1/-1":undefined,boxSizing:"border-box",textAlign:"center",borderRadius:7,
              border:`1px solid ${i===zone?"#ed9e74":stroke}`,background:i===zone?"#ffe6d6":"#fffaf3",fontSize:17,fontWeight:i===zone?730:500}}>{label}</div>)}
          </div>
        </div>
      </div>
    </aside>
    <Cursor x={pointerX} y={pointerY} opacity={Math.max(fleetCursor,structureCursor)} pressed={down}/>
    {f<65&&<Img src={dir("live-map.png")} style={{...position(0,0,1920,1080),opacity:mapOpacity}}/>}
    {f>=11&&f<83&&<div style={{...position(mix(sx-51,150,dock),mix(sy,595,dock),102,40),display:"grid",placeItems:"center",
      borderRadius:8,border:"1px solid #e88a59",background:"#ffe5d5",color:"#703b22",fontWeight:850,fontSize:23,
      opacity:ease(f,11,18)*(1-ease(f,70,83)),boxShadow:"0 5px 18px #6c3c2722"}}>M01</div>}
    {caption&&<div style={{position:"absolute",bottom:29,alignSelf:"center",background:"#231e1be9",color:"white",borderRadius:8,
      padding:"7px 18px",fontSize:30,fontWeight:650,opacity:ease(f,caption.from,caption.from+3)*(1-ease(f,caption.to-3,caption.to))}}>{caption.text}</div>}
    <Audio src={dir("voice.wav")}/><Audio src={dir("score.wav")}/>
  </AbsoluteFill>;
};
