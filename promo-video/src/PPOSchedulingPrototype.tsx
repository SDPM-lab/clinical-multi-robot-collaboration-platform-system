import { AbsoluteFill, Audio, Img, staticFile, useCurrentFrame } from "remotion";
import type { ReactNode } from "react";
import demo from "./ppo-scheduling-demo.json";
import captions from "./ppo-scheduling-captions.json";

const ink="#26201d", muted="#60524a", orange="#bd4b15", wire="#ed853f";
const field="#faf7f3";
const ramp=(f:number,a:number,b:number)=>Math.max(0,Math.min(1,(f-a)/(b-a)));
const ease=(f:number,a:number,b:number)=>{
  const t=ramp(f,a,b);return t*t*t*(10+t*(-15+6*t));
};
const layer={fontFamily:"Arial, 'Noto Sans CJK TC', sans-serif",color:ink};
const detail={fontSize:24,color:muted,lineHeight:1.35};
const text=(x:number,y:number)=>({position:"absolute" as const,left:x,top:y});

const Heading=({title,children}:{title:string;children?:ReactNode})=>
  <div style={{...text(134,125),maxWidth:1580}}>
    <div style={{fontSize:83,fontWeight:730,letterSpacing:"-.053em",lineHeight:1.02}}>{title}</div>
    {children&&<div style={{...detail,marginTop:20}}>{children}</div>}
  </div>;

const Tag=({children}:{children:ReactNode})=>
  <span style={{display:"inline-block",color:orange,background:"#fbeddf",borderRadius:6,padding:"6px 10px",fontSize:21,fontWeight:700}}>{children}</span>;

const Card=({x,y,width,height,children,active=false,opacity=1}:{x:number;y:number;width:number;height:number;
  children:ReactNode;active?:boolean;opacity?:number})=>
  <div style={{...text(x,y),width,height,boxSizing:"border-box",padding:"23px 28px",
    background:active?"#fff3e9":"#fffdfa",border:`1px solid ${active?"#eab184":"#e9dfd6"}`,
    borderRadius:14,boxShadow:active?"0 10px 24px #6e492414":"none",opacity}}>{children}</div>;

const Links=({children}:{children:ReactNode})=>
  <svg width="1920" height="1080" style={{position:"absolute",inset:0,pointerEvents:"none"}}>{children}</svg>;

const Link=({d,t,opacity=1}:{d:string;t:number;opacity?:number})=>
  <path d={d} pathLength={1} fill="none" stroke={wire} strokeWidth={3.2}
    strokeDasharray="1 1" strokeDashoffset={1-t} strokeLinecap="round" opacity={opacity}/>;

const taskTitle="Medication delivery";
const route="Pharmacy → Ward A";
const features=[
  {title:"Task requirements",body:"Type, priority, source & destination"},
  {title:"Robot state",body:"Capability, availability & battery"},
  {title:"Projected work",body:"Approach, queue & fleet load"},
];

const TaskData=({f}:{f:number})=><AbsoluteFill>
  <Heading title="Beyond automation.">Intelligent decisions begin with the task.</Heading>
  <Card x={135} y={350} width={636} height={345} active>
    <Tag>{demo.taskCode} · Pending</Tag>
    <div style={{fontSize:54,fontWeight:730,letterSpacing:"-.047em",marginTop:26}}>{taskTitle}</div>
    <div style={{...detail,marginTop:12}}>{route}</div>
    <div style={{...detail,marginTop:24}}>High priority · 15:05</div>
    <div style={{fontSize:22,marginTop:9,color:orange}}>Required capability · Medication delivery</div>
  </Card>
  <Links>{features.map(({title},i)=>
    <Link key={title} d={`M 771 520 H 864 Q 910 520 936 ${463+i*68} T 1039 ${405+i*147}`}
      t={ease(f,17+i*9,39+i*9)}/>)}</Links>
  {features.map(({title,body},i)=><Card key={title} x={1040} y={346+i*147} width={715} height={118}
    opacity={ease(f,28+i*9,47+i*9)}>
    <div style={{fontSize:33,fontWeight:700}}>{title}</div><div style={detail}>{body}</div>
  </Card>)}
</AbsoluteFill>;

const Candidates=({f}:{f:number})=>{
  const highlighted=ease(f,122,147);
  return <AbsoluteFill>
    <Heading title="Capability matching">Medication delivery · Apply eligibility rules to the fleet.</Heading>
    <div style={{...text(136,323),fontSize:25,fontWeight:700,color:orange}}>Task {demo.taskCode} · Candidate fleet</div>
    {demo.robots.map((r,i)=><Card key={r.id} x={134+i*238} y={403} width={220} height={258}
      active={r.eligible&&f>=122} opacity={ease(f,77+i*4,90+i*4)*(r.eligible?1:1-highlighted*.29)}>
      <div style={{fontSize:53,fontWeight:750,letterSpacing:"-.04em"}}>{r.id}</div>
      <div style={{...detail,textTransform:"capitalize",marginTop:4}}>{r.type}</div>
      <div style={{fontSize:22,color:muted,marginTop:15}}>{r.battery}% battery</div>
      <div style={{marginTop:15,fontSize:18,fontWeight:700,color:r.eligible?orange:muted,opacity:highlighted}}>
        {r.eligible?"Eligible":r.capabilityMatch?"Charging":"Capability mismatch"}
      </div>
    </Card>)}
    <div style={{...text(135,723),opacity:highlighted,fontSize:28,fontWeight:680}}>
      Eligible <span style={{color:orange,marginLeft:18}}>{demo.eligible.join("  ·  ")}</span>
    </div>
  </AbsoluteFill>;
};

const Decision=({f}:{f:number})=><AbsoluteFill>
  <Heading title="Intelligent decisions.">PPO Scheduling Concept</Heading>
  <Links>
    {features.map(({title},i)=><Link key={title} d={`M 622 ${376+i*154} C 735 ${376+i*154}, 737 531, 840 531`}
      t={ease(f,178+i*8,209+i*8)}/>)}
    <Link d="M 1245 531 C 1310 531, 1355 531, 1427 531" t={ease(f,231,255)}/>
  </Links>
  {features.map(({title,body},i)=><Card key={title} x={134} y={317+i*154} width={488} height={118}
    opacity={ease(f,165+i*4,177+i*4)}>
    <div style={{fontSize:28,fontWeight:730}}>{title}</div><div style={{...detail,fontSize:20}}>{body}</div>
  </Card>)}
  <Card x={840} y={424} width={406} height={215} active opacity={ease(f,200,228)}>
    <div style={{color:orange,fontSize:25,fontWeight:700}}>Masked actions</div>
    <div style={{fontSize:51,fontWeight:730,letterSpacing:"-.047em",marginTop:20}}>PPO policy</div>
    <div style={{...detail,fontSize:21,marginTop:10}}>Eligible set: {demo.eligible.join(" · ")}</div>
  </Card>
  <Card x={1427} y={448} width={345} height={164} opacity={ease(f,242,258)}>
    <div style={{fontSize:24,color:muted}}>Illustrative selection</div>
    <div style={{fontSize:57,fontWeight:750,marginTop:8,color:orange}}>{demo.robotId}</div>
  </Card>
</AbsoluteFill>;

const Assignment=({f}:{f:number})=>{
  const confirmed=ease(f,285,300);
  return <AbsoluteFill>
    <Heading title="Assignment confirmed.">Illustrative scheduling scenario</Heading>
    <Card x={134} y={380} width={630} height={255}>
      <Tag>Task {demo.taskCode}</Tag>
      <div style={{fontSize:53,letterSpacing:"-.045em",fontWeight:730,marginTop:22}}>{taskTitle}</div>
      <div style={{...detail,marginTop:12}}>{route}</div>
    </Card>
    <Links>
      <Link d="M 764 508 H 1002" t={ease(f,285,302)}/>
      <Link d="M 1490 508 H 1605 Q 1661 508 1661 564 V 745 Q 1661 789 1705 789 H 1920" t={ease(f,320,349)}/>
    </Links>
    <Card x={1002} y={374} width={488} height={268} active>
      <Tag>Assigned · Demo</Tag>
      <div style={{fontSize:110,letterSpacing:"-.065em",fontWeight:750,color:orange,marginTop:12}}>{demo.robotId}</div>
      <div style={detail}>Medical robot</div>
    </Card>
    <div style={{...text(1423,406),width:35,height:35,borderRadius:20,display:"grid",placeItems:"center",
      opacity:confirmed,background:"#fbe1d0",color:orange,fontSize:23,fontWeight:750}}>✓</div>
  </AbsoluteFill>;
};

const shots=[TaskData,Candidates,Decision,Assignment] as const;
const cuts=[75,165,285,360] as const;

export const PPOSchedulingPrototype=()=>{
  const f=useCurrentFrame();
  const index=cuts.findIndex(end=>f<end);
  const Shot=shots[Math.max(index,0)];
  const line=captions.find(item=>f>=item.from&&f<item.to);
  return <AbsoluteFill style={{...layer,background:field,overflow:"hidden"}}>
    <Shot f={f}/>
    <Img src={staticFile("dashboard-v2/brand-mark.svg")} style={{...text(138,62),width:49,height:34,objectFit:"contain"}}/>
    <div style={{...text(194,65),fontWeight:750,fontSize:28,letterSpacing:"-.044em"}}>Medi<span style={{color:orange}}>Sync</span></div>
    <div style={{position:"absolute",right:145,top:73,fontSize:18,color:muted}}>Illustrative Scheduling Scenario</div>
    {line&&<div style={{position:"absolute",bottom:47,left:0,right:0,textAlign:"center",fontSize:31,fontWeight:700}}>
      <span style={{background:"#261e1be8",color:"white",padding:"6px 15px",borderRadius:6}}>{line.text}</span>
    </div>}
    <Audio src={staticFile("ppo-scheduling/score.wav")} volume={.79}/>
    <Audio src={staticFile("ppo-scheduling/voice.wav")} volume={.91}/>
  </AbsoluteFill>;
};
