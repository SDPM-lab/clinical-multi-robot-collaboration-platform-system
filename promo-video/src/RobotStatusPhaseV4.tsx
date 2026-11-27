import {AbsoluteFill,Audio,Img,staticFile,useCurrentFrame} from "remotion";
import {Cursor,NativeCrop,Robot} from "./RobotStatusPhaseV2";
import capture from "./robot-status-phase-v2-capture.json";
import captions from "./robot-status-phase-v4-captions.json";

const ink="#231f1b", orange="#c3490e", paper="#faf7f3";
const asset=(file:string)=>staticFile("robot-status-phase-v4/"+file);
const titles=["KNOW YOUR ROBOT FLEET.","INTERACTIVE 3D ROBOT VIEW.","KEY STATUS. CLEAR AT A GLANCE.","CONNECTED ROBOT MANAGEMENT."];
const unit=(f:number,a:number,b:number)=>Math.min(1,Math.max(0,(f-a)/(b-a)));
const ease=(f:number,a:number,b:number)=>{const t=unit(f,a,b);return t*t*(3-2*t);};
const mix=(a:number,b:number,t:number)=>a+(b-a)*t;
type Box={x:number;y:number;width:number;height:number};
const rect=(b:Box)=>({position:"absolute" as const,left:b.x,top:b.y,width:b.width,height:b.height});
const between=(a:Box,b:Box,t:number):Box=>({
  x:mix(a.x,b.x,t),y:mix(a.y,b.y,t),width:mix(a.width,b.width,t),height:mix(a.height,b.height,t),
});
const page={x:112,y:109,width:1696,height:869};
const dock=(b:Box):Box=>({x:page.x+b.x*1.06,y:page.y+b.y*1.06,width:b.width*1.06,height:b.height*1.06});
const {row,m01,metrics,information,viewport}=capture;
const fleetRows=[row,{...row,y:mix(row.y,m01.y,.5)},m01];
const hero={x:175,y:124,width:1570,height:811};
const detailModel={x:66,y:288,width:1075,height:642};
const colors={green:"#177644",heat:"#963a22"};
function Gauge({temperature=false,progress}:{temperature?:boolean;progress:number}){
  const color=temperature?colors.heat:colors.green;
  const circumference=temperature?173:100;
  return <div style={{height:"100%",padding:"23px 25px",boxSizing:"border-box",background:temperature?"#fff8f2":"#f6faf3",
    borderRadius:16,border:"1px solid #e8ddd2",position:"relative",overflow:"hidden"}}>
    <div style={{fontSize:19,fontWeight:750}}>{temperature?"Temperature":"Battery"}</div>
    <div style={{position:"absolute",left:25,bottom:30,fontSize:62,fontWeight:750,letterSpacing:-3,whiteSpace:"nowrap"}}>
      {temperature?"36":"82"}<span style={{marginLeft:5,fontSize:25,letterSpacing:0}}>{temperature?"°C":"%"}</span>
    </div>
    {temperature?<svg width="112" height="100" viewBox="0 0 112 100" style={{position:"absolute",right:16,bottom:20}} aria-hidden>
      <path d="M16 78 A46 46 0 1 1 96 78" fill="none" stroke="#ead7cd" strokeWidth="9" strokeLinecap="round"/>
      <path d="M16 78 A46 46 0 1 1 96 78" fill="none" stroke={color} strokeWidth="9" strokeLinecap="round"
        pathLength={circumference} strokeDasharray={`${circumference*.36*progress} ${circumference}`}/>
    </svg>:<svg width="106" height="106" viewBox="0 0 106 106" style={{position:"absolute",right:16,bottom:20}} aria-hidden>
      <circle cx="53" cy="53" r="41" fill="none" stroke="#dce9db" strokeWidth="9"/>
      <circle cx="53" cy="53" r="41" fill="none" stroke={color} strokeWidth="9" pathLength={100}
        strokeDasharray={`${82*progress} 100`} strokeLinecap="round" transform="rotate(-90 53 53)"/>
    </svg>}
  </div>;
}
export const RobotStatusPhaseV4=()=>{
  const f=useCurrentFrame();
  const shot=f<75?0:f<165?1:f<270?2:3;
  const selection=f>=58;
  const listOut=ease(f,65,81);
  const heroIn=ease(f,69,88);
  const reframe=ease(f,159,197);
  const settle=ease(f,270,319);
  const plate=ease(f,286,323);
  const toNative=ease(f,309,334);
  const camera=mix(mix(132,209,ease(f,80,181)),132,ease(f,273,322));
  const model=between(between(hero,detailModel,reframe),dock(viewport),settle);
  const caption=captions.find(c=>f>=c.from&&f<c.to);
  const metricBoxes=[
    between({x:1129,y:270,width:328,height:192},dock({...metrics,width:metrics.width/2-5}),settle),
    between({x:1474,y:270,width:328,height:192},dock({...metrics,x:metrics.x+metrics.width/2+5,width:metrics.width/2-5}),settle),
  ];
  const infoBox=between({x:1129,y:490,width:673,height:288},dock(information),settle);

  return <AbsoluteFill style={{background:paper,color:ink,overflow:"hidden",fontFamily:"Inter,Arial,'Noto Sans CJK TC',sans-serif"}}>
    <div style={{position:"absolute",left:112,top:39,fontSize:47,letterSpacing:-1.45,fontWeight:850}}>{titles[shot]}</div>
    {(shot===2||shot===3)&&<div style={{position:"absolute",right:118,top:57,fontSize:16,fontWeight:620,color:"#735f50"}}>Demo Telemetry</div>}
    {f<82&&<div style={{position:"absolute",left:460,top:154,width:1000,height:743,opacity:1-listOut}}>
      <div style={{position:"absolute",left:190,top:9,width:620,height:684,borderRadius:27,background:"#eee7df",
        opacity:ease(f,3,16),clipPath:`inset(0 ${50*(1-ease(f,4,18))}% round 27px)`}}/>
      <div style={{position:"absolute",left:247,top:54,fontSize:29,fontWeight:780,opacity:ease(f,9,20)}}>Robot fleet</div>
      {fleetRows.map((box,i)=>{
        const t=ease(f,10+i*8,26+i*8);
        const isTarget=i===2;
        return <NativeCrop key={i} image={selection?"m01":"c01"} box={box} style={{
          left:247,top:121+i*174+36*(1-t),transform:"scale(1.5)",transformOrigin:"top left",
          opacity:t,borderRadius:11,boxShadow:isTarget&&selection?"0 10px 33px #d4774924":undefined,
        }}/>;
      })}
      {f>=39&&f<70&&<Cursor x={mix(887,690,ease(f,39,54))} y={mix(587,548,ease(f,39,54))}
        press={ease(f,55,58)*(1-ease(f,58,62))} opacity={ease(f,39,44)*(1-ease(f,63,70))}/>}
    </div>}
    {plate>0&&<Img src={staticFile("robot-status-phase-v2/m01.png")}
      style={{...rect(page),opacity:plate,borderRadius:14,boxShadow:"0 20px 64px #3c2b1e18",
        clipPath:`inset(${19*(1-plate)}% ${15*(1-plate)}% round 14px)`}}/>}
    {f>=65&&f<335&&<div style={{...rect(model),opacity:heroIn*(1-toNative),
      background:`radial-gradient(ellipse at 50% 47%,#fff 5%,${paper} 72%)`,
      clipPath:`inset(${35*(1-heroIn)}% ${22*(1-heroIn)}%)`}}>
      <div style={{position:"absolute",bottom:"8%",left:"34%",width:"32%",height:"5%",borderRadius:"50%",
        background:"radial-gradient(ellipse,#5d422f31,transparent 70%)",opacity:1-settle}}/>
      <Robot f={camera} showcase/>
    </div>}
    {f>=168&&f<334&&<>
      <div style={{position:"absolute",left:1129,top:198,fontSize:22,fontWeight:760,letterSpacing:.35,color:orange,
        opacity:ease(f,171,185)*(1-ease(f,275,296))}}>M01 · WARD A</div>
      {metricBoxes.map((b,i)=><div key={i} style={{...rect(b),opacity:ease(f,176+i*7,195+i*7)*(1-toNative),
        clipPath:`inset(0 0 0 ${100*(1-ease(f,176+i*7,195+i*7))}% round 16px)`}}>
        <div style={{width:328,height:192,transform:`scale(${b.width/328},${b.height/192})`,transformOrigin:"top left"}}>
          <Gauge temperature={i===1} progress={ease(f,188+i*7,219+i*7)}/>
        </div>
      </div>)}
      <div style={{...rect(infoBox),opacity:ease(f,198,215)*(1-toNative),
        clipPath:`inset(0 0 ${100*(1-ease(f,198,217))}% 0)`}}>
        <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",padding:"12px 0 0",columnGap:22,rowGap:22,borderTop:"1px solid #dbcec4"}}>
          {[["Status","Idle"],["Connection","Connected"],["Model","Agibot Genie G1"],["Robot type","Medical robot"]].map(([label,value],i)=>
            <div key={label} style={{opacity:ease(f,204+3*i,217+3*i)}}>
              <div style={{fontSize:16,color:"#67594f",fontWeight:620}}>{label}</div>
              <div style={{fontSize:25,fontWeight:760,marginTop:5,color:i<2?colors.green:ink}}>{value}</div>
            </div>)}
        </div>
      </div>
    </>}
    {caption&&<div style={{position:"absolute",bottom:27,alignSelf:"center",background:"#231e1bea",color:"white",
      borderRadius:8,padding:"7px 17px",fontSize:30,fontWeight:650}}>{caption.text}</div>}
    <Audio src={asset("voice.wav")}/><Audio src={asset("score.wav")}/>
  </AbsoluteFill>;
};
