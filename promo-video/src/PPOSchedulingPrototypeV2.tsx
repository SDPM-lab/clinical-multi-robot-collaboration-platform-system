import {AbsoluteFill, Audio, Img, staticFile, useCurrentFrame} from "remotion";
import type {ReactNode} from "react";
import frames from "./ppo-spatial-plates.json";
import captions from "./ppo-spatial-captions.json";

const ink="#241e1a", gray="#62574e", accent="#aa461a";
const point=(left:number,top:number)=>({position:"absolute" as const,left,top});
const progress=(f:number,a:number,b:number)=>{
  const t=Math.max(0,Math.min(1,(f-a)/(b-a)));
  return t*t*t*(10+t*(-15+6*t));
};
const Title=({children,top=170,size=76}:{children:ReactNode;top?:number;size?:number})=>
  <div style={{...point(135,top),fontSize:size,fontWeight:760,lineHeight:1.03,letterSpacing:"-.053em"}}>{children}</div>;
const Info=({title,children,top,alpha=1}:{title:string;children:ReactNode;top:number;alpha?:number})=>
  <div style={{...point(138,top),width:525,borderLeft:"2px solid #d9956d",paddingLeft:17,opacity:alpha}}>
    <div style={{fontSize:29,fontWeight:730,letterSpacing:"-.026em"}}>{title}</div>
    <div style={{fontSize:21,color:gray,lineHeight:1.38,marginTop:5}}>{children}</div>
  </div>;

const labels=["Pharmacy","Ward A","Nurse Station","M01","M02","C01","C02","W01","W02","W03"];
const World=({f}:{f:number})=>{
  const [frame,points]=(frames as unknown as [number,Record<string,number[]>][])[f];
  return <div style={{...point(527,135),width:1340,height:791}}>
    <Img src={staticFile(`ppo-spatial/plates/${frame}.png`)}
      style={{width:"100%",height:"100%",display:"block"}} />
    {labels.map(name=>{
      const p=points[name];
      if(!p||Math.abs(p[0])>.99||Math.abs(p[1])>.93)return null;
      const charge=/^W0[1-3]$/.test(name)?Number(name.slice(1))-2:0;
      return <div key={name} style={{position:"absolute",
        left:`${(p[0]+1)*50+charge*2.7}%`,top:`${(1-p[1])*50+charge*3}%`,
        transform:"translate(-50%,-100%)",border:"1px solid #ecd8c9",borderRadius:6,padding:"4px 7px",
        background:name.startsWith("M")?"#fff0e1":"#fffaf2ee",color:name.startsWith("M")?accent:gray,
        fontSize:18,fontWeight:720,whiteSpace:"nowrap"}}>{name}</div>;
    })}
  </div>;
};

export const PPOSchedulingPrototypeV2=()=>{
  const f=useCurrentFrame();
  const line=captions.find(c=>f>=c.from&&f<c.to);
  return <AbsoluteFill style={{background:"#faf6f0",fontFamily:"Arial, 'Noto Sans CJK TC', sans-serif",
    color:ink,overflow:"hidden"}}>
    <World f={f}/>
    {f<90&&<>
      <div style={{...point(136,121),fontSize:24,fontWeight:750,color:accent}}>T0002 · Medication delivery</div>
      <Title top={170}>The task,<br/>in context.</Title>
      <Info title="Task requirements" top={410} alpha={progress(f,6,21)}>High priority · Pharmacy → Ward A</Info>
      <Info title="Robot state" top={511} alpha={progress(f,20,38)}>Capability, availability and battery</Info>
      <Info title="Projected work" top={612} alpha={progress(f,36,54)}>Approach time, queue and fleet load</Info>
    </>}
    {f>=90&&f<180&&<>
      <Title>Capability<br/>matching.</Title>
      <Info title="Eligible for T0002" top={423} alpha={progress(f,117,139)}>M01 and M02</Info>
      <Info title="Outside the action mask" top={538} alpha={progress(f,127,148)}>
        C01 / C02 · Capability mismatch<br/>W01 / W02 / W03 · Charging
      </Info>
    </>}
    {f>=180&&f<238&&<>
      <Title size={70}>98-Dimensional<br/>State</Title>
      <Info title="41 · Task requirements" top={382}>5 type + 4 priority + 16 source + 16 destination</Info>
      <Info title="35 · Robot state" top={485} alpha={progress(f,185,200)}>7 robots × 5 state features</Info>
      <Info title="22 · Projected work" top={587} alpha={progress(f,195,210)}>7 × 3 work features + 1 fleet load imbalance</Info>
    </>}
    {f>=238&&f<300&&<>
      <div style={{...point(136,129),fontSize:22,color:accent,fontWeight:750}}>PPO · Proximal Policy Optimization</div>
      <Title top={180} size={68}>One trained policy.</Title>
      <Info title="Training · before deployment" top={346}>State → Action → Reward → Policy update</Info>
      <Info title="Inference · during scheduling" top={482} alpha={progress(f,239,247)}>
        Current state → Trained PPO → Assignment
      </Info>
      <Info title="Action mask" top={614}>Limits the policy to eligible robots.</Info>
    </>}
    {f>=300&&f<390&&<>
      <div style={{...point(136,161),fontSize:24,color:accent,fontWeight:750}}>T0002 · Medication delivery</div>
      <Title top={220} size={78}>Assigned to<br/>M01.</Title>
      <Info title="Pharmacy → Ward A" top={438}>Demo assignment</Info>
    </>}
    {f>=390&&<>
      <div style={{...point(136,161),fontSize:24,color:accent,fontWeight:750}}>T0002 · Assigned</div>
      <Title top={220} size={76}>M01 in the<br/>hospital.</Title>
      <Info title="L1 · Pharmacy" top={438}>Demo assignment</Info>
    </>}
    <Img src={staticFile("dashboard-v2/brand-mark.svg")} style={{...point(137,53),width:44,height:32,objectFit:"contain"}}/>
    <div style={{...point(190,56),fontWeight:750,fontSize:27,letterSpacing:"-.044em"}}>Medi<span style={{color:accent}}>Sync</span></div>
    {line&&<div style={{position:"absolute",bottom:45,left:0,right:0,textAlign:"center",fontSize:30,fontWeight:700}}>
      <span style={{background:"#261e1be8",color:"white",padding:"6px 15px",borderRadius:6}}>{line.text}</span>
    </div>}
    <Audio src={staticFile("ppo-spatial/score.wav")} volume={.79}/>
    <Audio src={staticFile("ppo-spatial/voice.wav")} volume={.91}/>
  </AbsoluteFill>;
};
