import {AbsoluteFill, Audio, Easing, Img, interpolate, staticFile, useCurrentFrame} from "remotion";
import demo from "./ppo-scheduling-demo.json";
import captions from "./ppo-v6-captions.json";

const white = "#fffaf6";
const ink = "#211b18";
const orange = "#ee531c";
const brown = "#63564e";
const hair = "#eadbd0";
const peach = "#ffe6d9";
const clamp = {extrapolateLeft:"clamp", extrapolateRight:"clamp"} as const;
const go = (f:number,a:number,b:number) => interpolate(f,[a,b],[0,1],{...clamp,easing:Easing.bezier(.31,0,.25,1)});
const mix = (a:number,b:number,t:number) => a+(b-a)*t;

function Words({x,y,en,zh,size=58}: {x:number;y:number;en:string;zh:string;size?:number}) {
  return <text x={x} y={y} fill={ink} fontSize={size} fontWeight="750">
    {en}<tspan x={x+2} dy={size*.83} fill={brown} fontSize={size*.47} fontWeight="500">{zh}</tspan>
  </text>;
}
function Robot({x,y,s=1,fg=ink}: {x:number;y:number;s?:number;fg?:string}) {
  return <g transform={`translate(${x} ${y}) scale(${s})`} stroke={fg} fill="none" strokeWidth="4.5" strokeLinecap="round" strokeLinejoin="round">
    <rect x="-25" y="-18" width="50" height="36" rx="12"/>
    <path d="M0 -19v-9m-5 0h10m-35 19v13m60-13v13m-43 14v10h27v-10"/>
    <path d="M-9 -3v1m18-1v1" strokeWidth="6"/>
  </g>;
}
function Trace({d,p,width=5}: {d:string;p:number;width?:number}) {
  return <><path d={d} fill="none" stroke={hair} strokeWidth={width}/>
    <path d={d} fill="none" pathLength="1" stroke={orange} strokeWidth={width} strokeLinecap="round" strokeDasharray={`${p} 1`}/></>;
}
const slots = [[915,358],[1185,358],[1455,358],[1725,358],[1050,655],[1320,655],[1590,655]];
const featureColors = [orange,"#ae745d",ink];
const featureIndex = (i:number) => i<41 ? 0 : i<97 ? 1 : 2;
const taskFill = "#30231d";

function Intro({f}: {f:number}) {
  const title=go(f,14,46);
  return <>
    <text x="121" y="554" fill={orange} fontSize={mix(320,296,title)} fontWeight="850" letterSpacing="-14">PPO</text>
    <g clipPath="url(#v7Intro)">
      <Words x={130} y={657} en="Proximal Policy Optimization" zh="近端策略最佳化" size={57}/>
      <text x="132" y="797" fontSize="32" fill={brown}>Reinforcement learning for robot scheduling</text>
    </g>
    <defs><clipPath id="v7Intro"><rect x="124" y="582" width="1040" height={234*title}/></clipPath></defs>
    {slots.map(([x,y],i)=>{
      const p=go(f,38+i*2,66+i*2);
      const handoff=go(f,75,89);
      const cx=mix(1050+x*.38,x,handoff);
      const cy=mix(164+y*.83,y,handoff);
      return <g key={i} opacity={p}><rect x={cx-66} y={cy-66} width="132" height="132" rx={mix(20,66,handoff)}
        fill={i===2||i===3?peach:"#f1e3d9"} stroke={hair} strokeWidth="2"/>
        <path d={`M${cx-27} ${cy+20}v-35m27 35v-56m27 56v-28`} stroke={i===2||i===3?orange:"#bd9582"} strokeWidth="11" strokeLinecap="round" opacity={1-handoff}/>
        <g opacity={handoff}><Robot x={cx} y={cy} s={1.43}/></g>
      </g>;
    })}
  </>;
}
function Fleet({f}: {f:number}) {
  const p=go(f,113,155);
  const reveal=go(f,90,110);
  return <>
    <g opacity={reveal}>
      <path d="M124 230 H654 L720 296 V855 H124Z" fill={taskFill}/>
      <text x="175" y="339" fontSize="32" fontWeight="750" fill="#ffb18f">TASK REQUIREMENTS</text>
      <text x="170" y="509" fontSize="112" fontWeight="850" fill={white}>T0002</text>
      <text x="178" y="613" fontSize="45" fontWeight="700" fill={white}>Medication delivery</text>
      <text x="179" y="683" fontSize="36" fill="#e5c7b7">Pharmacy → Ward A</text>
      <text x="179" y="779" fontSize="30" fontWeight="750" fill="#ffad88">HIGH PRIORITY</text>
      <Words x={831} y={191} en="7 Robot Candidates" zh="七台候選機器人｜依能力與可用性篩選" size={50}/>
    </g>
    {demo.robots.map((robot,i)=>{
      const [x,y]=slots[i];
      const dy=robot.eligible?-19*p:11*p;
      return <g key={robot.id} transform={`translate(${x} ${y+dy})`}>
        <circle r="66" fill={robot.eligible?peach:"#f1e3d9"} stroke={robot.eligible?orange:hair} strokeWidth={mix(2,robot.eligible?5:2,p)} opacity={robot.eligible?1:1-.36*p}/>
        <Robot x={0} y={0} s={1.43} fg={robot.eligible?"#a13a15":brown}/>
        <g opacity={reveal}>
          <text y="114" textAnchor="middle" fontSize="43" fontWeight="800">{robot.id}</text>
          <text y="149" textAnchor="middle" fontSize="23" fontWeight={robot.eligible?750:500}
            fill={robot.eligible?"#a13a15":brown} opacity={p}>{robot.eligible?"Eligible":robot.capabilityMatch?"Charging / Unavailable":"Capability Mismatch"}</text>
        </g>
      </g>;
    })}
  </>;
}
function State({f}: {f:number}) {
  const p=go(f,200,249);
  const handoff=go(f,180,200);
  const into=go(f,259,269);
  const labels=["Task information","Robot fleet state","System workload"];
  const detail=["任務・類型、優先級、起訖點","車隊・能力、可用性、電量等","系統・全域負載不均衡"];
  return <>
    <g opacity={1-into}>
      <Words x={126} y={228} en="98-Dimensional State" zh="將多源資訊整理成 98 維狀態輸入" size={66}/>
      {labels.map((label,i)=><g key={label} transform={`translate(0 ${330+i*171})`}>
        <path d="M125 0H658" stroke={featureColors[i]} strokeWidth="3"/>
        <Words x={126} y={57} en={label} zh={detail[i]} size={42}/>
        <text x="133" y="133" fontSize="24" fill={featureColors[i]} fontWeight="700">{[41,56,1][i]} FEATURES</text>
      </g>)}
    </g>
    {Array.from({length:98},(_,i)=>{
      const g=featureIndex(i),j=i-[0,41,97][g];
      const join=go(f,200+g*6,235+g*6);
      const node=slots[j%7];
      const fromFleet=g===1 && j<7;
      const x=mix(fromFleet?mix(node[0]-24,794+j%12*72,handoff):794+j%12*72,790+i%14*70,join);
      const y=mix(fromFleet?mix(node[1]-11,510,handoff):333+g*177+Math.floor(j/12)*28,284+Math.floor(i/14)*84,join);
      return <rect key={i} x={mix(x,350+i%7*7,into)} y={mix(y,435+Math.floor(i/7)*10,into)}
        width={mix(mix(g===2?216:49,57,p),5,into)} height={mix(mix(18,67,p),8,into)} rx={mix(8,2,into)}
        fill={featureColors[g]} opacity={mix(.92,.68,into)}/>;
    })}
  </>;
}
const columns=[
  {x:400,ys:[380,500,620,740]},
  {x:703,ys:[235,360,485,610,735,860]},
  {x:1038,ys:[294,439,584,729]},
  {x:1370,ys:[382,558,734]},
  {x:1575,ys:[558]},
];
function Mesh({f,update=0}: {f:number;update?:number}) {
  return <>
    {columns.slice(0,-1).flatMap(({x,ys},i)=>ys.flatMap((y,j)=>columns[i+1].ys.map((end,k)=>{
      const next=columns[i+1].x;
      const p=go(f,273+i*6+j,289+i*6+j);
      const strong=(i+j+k)%3===0;
      const d=`M${x} ${y} C${x+140} ${y} ${next-130} ${end} ${next} ${end}`;
      return <g key={d}>
        <path d={d} fill="none" stroke={hair} strokeWidth="3" opacity={.12+.65*p}/>
        {strong && <path d={d} fill="none" stroke={orange} strokeWidth={mix(5,3,update)}
          opacity={mix(.8,.56,update)} pathLength="1" strokeDasharray={`${p} 1`}/>}
      </g>;
    })))}
    {columns.flatMap(({x,ys},i)=>ys.map((y,j)=>{
      const p=go(f,271+i*7+j*2,284+i*7+j*2);
      return <circle key={`${x}-${y}`} cx={x} cy={y} r={mix(14,28+i*3,p)} fill={(i+j)%3===0?orange:peach}
        stroke={orange} strokeWidth="3" opacity={.18+.82*p}/>;
    }))}
  </>;
}
function Input({f}: {f:number}) {
  const push=go(f,273,309);
  return <>
    <g transform={`translate(${-32*push} ${-88*push}) scale(${1+.17*push})`}><Mesh f={f}/></g>
    {Array.from({length:98},(_,i)=><rect key={i} x={350+i%7*7} y={435+Math.floor(i/7)*10} width="5" height="8" fill={featureColors[featureIndex(i)]}/>)}
    <rect x="116" y="767" width="568" height="171" rx="22" fill={white}/>
    <Words x={124} y={833} en="Inside the PPO network" zh="狀態輸入逐層傳遞｜概念示意" size={54}/>
    <text x="126" y="487" fontSize="76" fontWeight="850" fill={orange}>98D</text>
    <text x="130" y="539" fontSize="27" fill={brown}>STATE INPUT</text>
  </>;
}
function Focus({f,actor}: {f:number;actor:boolean}) {
  const p=go(f,actor?311:337,actor?329:353);
  return <>
    <path d="M-50 300Q300 330 565 556M-50 550H565M-50 835Q300 806 565 556" fill="none" stroke={hair} strokeWidth="11"/>
    <circle cx="565" cy="556" r="124" fill={peach} stroke={orange} strokeWidth="5"/>
    <circle cx="565" cy="556" r="41" fill={orange}/>
    <Words x={124} y={231} en={actor?"Actor":"Critic"} zh={actor?"策略輸出｜決定採取什麼動作":"價值估計｜評估目前狀態"} size={91}/>
    {actor ? <>
      <Trace d="M565 556 Q778 556 931 389 H1400" p={p} width={10}/>
      <Trace d="M565 556 Q778 556 931 723 H1400" p={go(f,314,332)} width={10}/>
      {[389,723].map((y,i)=><g key={y} opacity={go(f,315+i*3,325+i*3)}>
        <circle cx="1410" cy={y} r="111" fill={peach} stroke={orange} strokeWidth="4"/>
        <Robot x={1410} y={y} s={2.34}/>
        <text x="1554" y={y+14} fontSize="51" fontWeight="800">{demo.eligible[i]}</text>
        <text x="1558" y={y+54} fontSize="24" fill={brown}>ELIGIBLE ACTION</text>
      </g>)}
    </> : <>
      <Trace d="M565 556 H1100" p={p} width={10}/>
      <path d="M1100 463 H1730 V668 H1100Z" fill={peach}/>
      <path d="M1145 530 H1681" stroke="#dec1b0" strokeWidth="34" strokeLinecap="round"/>
      <path d={`M1145 530 H${mix(1146,1497,p)}`} stroke={orange} strokeWidth="34" strokeLinecap="round"/>
      <path d={`M${mix(1150,1497,p)} 498 v64`} stroke={ink} strokeWidth="6"/>
      <text x="1147" y="623" fontSize="45" fontWeight="750">State value</text>
    </>}
  </>;
}
function Feedback({f}: {f:number}) {
  const update=go(f,392,418);
  return <>
    <g opacity={1-update}>
      <Words x={124} y={226} en="Learning from feedback" zh="動作、環境回應與獎勵形成訓練經驗" size={63}/>
      <Trace d="M248 463 H1655 V718 H704" p={go(f,362,398)} width={9}/>
      {["Action","Environment response","Reward signal"].map((label,i)=><g key={label} opacity={go(f,360+i*6,368+i*6)}>
        <path d={`M${126+i*563} 349 h448 l34 34 v171 h-482Z`} fill={i===2?peach:"#f1e3d9"}/>
        <text x={155+i*563} y="436" fontSize="28" fill={orange} fontWeight="800">0{i+1}</text>
        <text x={155+i*563} y="506" fontSize="38" fontWeight="750">{label}</text>
      </g>)}
      <g opacity={go(f,380,391)}>
        <rect x="124" y="652" width="847" height="139" rx="22" fill={taskFill}/>
        <text x="174" y="739" fontSize="54" fontWeight="750" fill={white}>Training experience</text>
      </g>
    </g>
    <g opacity={update}>
      <Words x={124} y={225} en="Policy Update" zh="策略更新｜從收集的經驗與回饋學習" size={64}/>
      <g transform={`translate(${240*update} ${214*update}) scale(${mix(.92,.43,update)})`}><Mesh f={320} update={update}/></g>
      <circle cx="962" cy="556" r={178*update} fill={taskFill}/>
      <text x="962" y="568" textAnchor="middle" fontSize="47" fill={white} fontWeight="800" opacity={update}>PPO Policy</text>
    </g>
  </>;
}
function Inference({f}: {f:number}) {
  const p=go(f,429,455);
  const route=go(f,453,492);
  return <>
    <g opacity={1-p}><Words x={124} y={231} en="Offline training" zh="離線訓練｜從經驗更新策略" size={65}/></g>
    <g opacity={p}>
      <Words x={124} y={231} en="Inference" zh="實際派工｜使用已訓練的策略" size={72}/>
      <Trace d="M406 556 H1537" p={route} width={10}/>
      <path d="M126 409H494L533 448V705H126Z" fill={peach}/>
      <text x="161" y="519" fontSize="49" fontWeight="800">Current state</text>
      {Array.from({length:32},(_,i)=><rect key={i} x={162+i%16*19} y={577+Math.floor(i/16)*31} width="14" height="22" rx="2" fill={featureColors[i%3]}/>)}
      <circle cx="1537" cy="556" r="133" fill={peach} stroke={orange} strokeWidth="4"/>
      <Robot x={1537} y={556} s={2.65}/>
      <text x="1537" y="762" textAnchor="middle" fontSize="41" fontWeight="750">Assignment</text>
    </g>
    <circle cx="962" cy="556" r="178" fill={taskFill}/>
    <text x="962" y={mix(568,555,p)} textAnchor="middle" fontSize="47" fill={white} fontWeight="800">PPO Policy</text>
    <text x="962" y="619" textAnchor="middle" fill="#ffb089" fontSize="32" fontWeight="750" opacity={p}>TRAINED</text>
  </>;
}
function Assignment({f}: {f:number}) {
  const p=go(f,510,546);
  return <>
    <g opacity={go(f,510,527)}>
      <Words x={124} y={226} en="Intelligent Task Assignment" zh="智慧任務指派" size={65}/>
      <path d="M124 345H766L832 411V842H124Z" fill={taskFill}/>
      <text x="178" y="495" fontSize="34" fontWeight="750" fill="#ffb089">TASK</text>
      <text x="165" y="655" fontSize="139" fontWeight="850" fill={white}>{demo.taskCode}</text>
      <text x="180" y="739" fontSize="43" fill={white}>Medication Delivery</text>
      <Trace d="M832 556 H1278" p={p} width={10}/>
    </g>
    <circle cx={mix(1537,1348,p)} cy="556" r={mix(133,217,p)} fill={peach} stroke={orange} strokeWidth="4"/>
    <Robot x={mix(1537,1348,p)} y={556} s={mix(2.65,4.38,p)}/>
    <g opacity={go(f,525,549)}>
      <text x="1348" y="852" textAnchor="middle" fontSize="68" fontWeight="800">Assigned Robot M01</text>
      <text x="1348" y="909" textAnchor="middle" fontSize="28" fill={brown}>示範指派｜DEMO ASSIGNMENT</text>
    </g>
  </>;
}
function Scene({f}: {f:number}) {
  if(f<90)return <Intro f={f}/>;
  if(f<180)return <Fleet f={f}/>;
  if(f<270)return <State f={f}/>;
  if(f<312)return <Input f={f}/>;
  if(f<338)return <Focus f={f} actor/>;
  if(f<362)return <Focus f={f} actor={false}/>;
  if(f<420)return <Feedback f={f}/>;
  if(f<510)return <Inference f={f}/>;
  return <Assignment f={f}/>;
}
export const PPOSchedulingPrototypeV7 = () => {
  const f=useCurrentFrame();
  const caption=captions.find(({from,to})=>f>=from&&f<to);
  return <AbsoluteFill style={{background:white,fontFamily:"Inter, Arial, Noto Sans CJK TC, sans-serif"}}>
    <svg width="1920" height="1080" fill={ink}><Scene f={f}/></svg>
    <div style={{position:"absolute",left:126,top:58,display:"flex",alignItems:"center",gap:10,color:ink,fontSize:32,fontWeight:750}}>
      <Img src={staticFile("dashboard-v2/brand-mark.svg")} style={{width:45,height:37}} alt=""/><span>Medi<span style={{color:orange}}>Sync</span></span>
    </div>
    {caption&&<div style={{position:"absolute",alignSelf:"center",bottom:43,background:ink,color:white,fontSize:32,borderRadius:8,padding:"9px 22px"}}>{caption.text}</div>}
    <Audio src={staticFile("ppo-v6/voice.wav")}/>
    <Audio src={staticFile("ppo-v7/score.wav")}/>
  </AbsoluteFill>;
};
