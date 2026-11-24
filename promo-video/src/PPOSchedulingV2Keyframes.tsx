import {AbsoluteFill, Img, staticFile, useCurrentFrame} from "remotion";
import anchors from "./ppo-spatial-anchors.json";

type Point=readonly number[];
const ink="#241e1a", gray="#655951", accent="#be4d15";
const pos=(left:number,top:number)=>({position:"absolute" as const,left,top});
const mark=(name:string)=>staticFile(`ppo-spatial/${name}.png`);
const label=(x:number,y:number)=>({...pos(x,y),fontSize:25,fontWeight:720,color:accent});

const Render3D=({name,x,y,w}:{name:string;x:number;y:number;w:number})=>
  <Img src={mark(name)} style={{...pos(x,y),width:w,height:w*9/16}} />;

const PlaceLabel=({name,point,x,y,w,dx=0,dy=0,active=false}:{
  name:string;point:Point;x:number;y:number;w:number;dx?:number;dy?:number;active?:boolean;
})=><div style={{...pos(x+point[0]*w+dx,y+point[1]*w*9/16+dy),transform:"translate(-50%, -100%)",
  color:active?accent:gray,background:active?"#fff1e4":"#fffcf6ee",border:"1px solid #ebdace",
  padding:"6px 10px",borderRadius:7,fontWeight:720,fontSize:20,whiteSpace:"nowrap",
  boxShadow:"0 4px 12px #4b322519"}}>{name}</div>;

const Title=({text,x=135,y=128,size=80}:{text:string;x?:number;y?:number;size?:number})=>
  <div style={{...pos(x,y),fontSize:size,fontWeight:760,letterSpacing:"-.055em",lineHeight:1.01,
    whiteSpace:"pre-line"}}>{text}</div>;

const Steps=({heading,body,x,y}:{heading:string;body:string;x:number;y:number})=>
  <div style={{...pos(x,y),maxWidth:500,borderLeft:"2px solid #d8885b",paddingLeft:18}}>
    <div style={{fontSize:30,fontWeight:730,letterSpacing:"-.025em"}}>{heading}</div>
    <div style={{fontSize:22,color:gray,marginTop:5,lineHeight:1.35}}>{body}</div>
  </div>;

export const PPOSchedulingV2Keyframes=()=>{
  const f=useCurrentFrame();
  const stage=f===0?"hospital":f===1?"candidates":f===2?"matrix":f===4?"hero":"match";
  return <AbsoluteFill style={{fontFamily:"Arial, sans-serif",color:ink,background:"#faf6f0",overflow:"hidden"}}>
    {f===0&&<>
      <Render3D name={stage} x={500} y={190} w={1345} />
      <div style={label(136,111)}>T0002 · Medication delivery</div>
      <Title text={"The task,\nin context."} y={163} size={88}/>
      <Steps heading="Task requirements" body="High priority · Pharmacy → Ward A" x={137} y={435}/>
      <Steps heading="Robot state" body="Capability, availability and battery" x={137} y={537}/>
      <Steps heading="Projected work" body="Approach time, queued work and fleet load" x={137} y={639}/>
      {Object.entries(anchors.hospital).map(([name,point])=><PlaceLabel key={name} name={name} point={point} x={500} y={190} w={1345} active={name==="Pharmacy"}/>)}
    </>}
    {f===1&&<>
      <Render3D name={stage} x={390} y={147} w={1450} />
      <Title text={"Capability\nmatching."} y={165} size={86}/>
      <Steps heading="Eligible for T0002" body="M01 and M02" x={138} y={414}/>
      <Steps heading="Outside the action mask" body={"C01 / C02 · capability mismatch\nW01 / W02 / W03 · charging"} x={138} y={529}/>
      {Object.entries(anchors.candidates).filter(([name])=>!name.startsWith("W")).map(([name,point])=>
        <PlaceLabel key={name} name={name} point={point} x={390} y={147} w={1450} active={name.startsWith("M")}/>)}
      <PlaceLabel name="W01 / W02 / W03" point={anchors.candidates.W02} x={390} y={147} w={1450} dy={-22}/>
    </>}
    {f===2&&<>
      <Render3D name={stage} x={654} y={170} w={1170}/>
      <Title text={"98-Dimensional\nState"} y={183} size={78}/>
      <Steps heading="41 · Task requirements" body="5 type + 4 priority + 16 source + 16 destination" x={137} y={406}/>
      <Steps heading="35 · Robot state" body="7 robots × 5 capability, availability and battery flags/values" x={137} y={527}/>
      <Steps heading="22 · Projected work" body="7 × 3 work features + 1 fleet load imbalance" x={137} y={651}/>
      <div style={{...label(137,806),fontSize:20}}>Feature groups · simplified spatial representation</div>
    </>}
    {f===3&&<>
      <Render3D name="matrix" x={42} y={243} w={690}/>
      <Title text="One trained policy." y={132} size={79}/>
      <div style={{...pos(771,331),width:1000,borderBottom:"1px solid #e5d6c7",paddingBottom:62}}>
        <div style={{fontSize:25,color:accent,fontWeight:720,marginBottom:20}}>Training · before deployment</div>
        <div style={{fontSize:39,fontWeight:720,letterSpacing:"-.03em"}}>State → Action → Reward → Policy update</div>
      </div>
      <div style={{...pos(771,546),width:1000}}>
        <div style={{fontSize:25,color:accent,fontWeight:720,marginBottom:20}}>Inference · during scheduling</div>
        <div style={{fontSize:37,fontWeight:720,letterSpacing:"-.03em"}}>Current state → Trained PPO → Assignment</div>
        <div style={{fontSize:22,color:gray,marginTop:16}}>The action mask limits the policy to eligible robots.</div>
      </div>
      <div style={{...pos(137,835),fontSize:22,color:gray}}>PPO · Proximal Policy Optimization</div>
    </>}
    {f===4&&<>
      <Render3D name={stage} x={660} y={82} w={1280}/>
      <div style={label(136,190)}>T0002 · Medication delivery</div>
      <Title text="Assigned to M01." y={256} size={81}/>
      <div style={{...pos(139,382),fontSize:30,color:gray}}>Pharmacy → Ward A</div>
      <div style={{...pos(139,468),fontSize:21,color:gray}}>Demo assignment</div>
    </>}
    {f===5&&<>
      <Render3D name={stage} x={485} y={160} w={1350}/>
      <div style={label(136,176)}>T0002 · Assigned</div>
      <Title text={"M01 in\nthe hospital."} y={234} size={78}/>
      <div style={{...pos(139,443),fontSize:25,color:gray}}>L1 · Pharmacy</div>
      <PlaceLabel name="M01" point={anchors.match.M01} x={485} y={160} w={1350} dy={-5} active/>
    </>}
    <Img src={staticFile("dashboard-v2/brand-mark.svg")} style={{...pos(137,54),width:46,height:32,objectFit:"contain"}}/>
    <div style={{...pos(190,55),fontSize:28,fontWeight:750,letterSpacing:"-.045em"}}>Medi<span style={{color:accent}}>Sync</span></div>
  </AbsoluteFill>;
};
