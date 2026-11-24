import {AbsoluteFill, Audio, Easing, Img, interpolate, staticFile, useCurrentFrame} from "remotion";
import demo from "./ppo-scheduling-demo.json";
import captions from "./ppo-v8-captions.json";

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
  const title=go(f,10,31);
  return <>
    <text x="121" y="554" fill={orange} fontSize={mix(320,296,title)} fontWeight="850" letterSpacing="-14">PPO</text>
    <g clipPath="url(#v7Intro)">
      <Words x={130} y={657} en="Proximal Policy Optimization" zh="近端策略最佳化" size={57}/>
      <text x="132" y="797" fontSize="32" fill={brown}>Reinforcement learning for robot scheduling</text>
    </g>
    <defs><clipPath id="v7Intro"><rect x="124" y="582" width="1040" height={234*title}/></clipPath></defs>
    {slots.map(([x,y],i)=>{
      const p=go(f,26+i*2,43+i*2);
      const handoff=go(f,48,59);
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
  const p=go(f,89,126);
  const reveal=go(f,60,84);
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
  const p=go(f,173,218);
  const handoff=go(f,150,173);
  const into=go(f,230,239);
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
      const join=go(f,173+g*6,203+g*6);
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

const layers = [
  {x:537,ys:[448,546,644]},
  {x:729,ys:[389,490,591,692]},
  {x:916,ys:[448,546,644]},
  {x:1091,ys:[546]},
];
const fade = (f:number,a:number,b:number) => 1-go(f,a,b);

function NetworkMesh({f}: {f:number}) {
  const update=go(f,474,498);
  return <>
    {layers.slice(0,-1).flatMap(({x,ys},i)=>ys.flatMap((y,j)=>layers[i+1].ys.map((nextY,k)=>{
      const nextX=layers[i+1].x;
      const path=`M${x} ${y} C${x+86} ${y} ${nextX-86} ${nextY} ${nextX} ${nextY}`;
      const visible=go(f,249+i*11+j,274+i*11+j);
      return <g key={path}>
        <path d={path} stroke={hair} strokeWidth="3" fill="none"/>
        {(i+j+k)%3===0 && <path d={path} pathLength="1" fill="none" stroke={orange}
          strokeWidth={mix(4.2,(j+k)%2===0?2.3:5.1,update)} strokeDasharray={`${visible} 1`}/>}
      </g>;
    })))}
    {layers.flatMap(({x,ys},i)=>ys.map((y,j)=><circle key={`${x}-${y}`} cx={x} cy={y} r={21+i*2}
      fill={(i+j)%3===0?orange:peach} opacity={mix(.30,1,go(f,243+i*10+j*2,268+i*10+j*2))}
      stroke={orange} strokeWidth="2.5"/>))}
  </>;
}
const trainingSteps = [
  {en:"State → Action",zh:"狀態進入策略並產生動作",x:144,at:418},
  {en:"Environment Feedback",zh:"環境依動作提供回饋",x:429,at:425},
  {en:"Reward",zh:"獎勵訊號",x:774,at:436},
  {en:"Training Experience",zh:"收集訓練經驗",x:985,at:448},
  {en:"Advantage Estimation",zh:"估計動作相對於預期的表現",x:1277,at:462},
];
function TrainingPath({f}: {f:number}) {
  const alpha=fade(f,503,522);
  return <g opacity={alpha}>
    <path d="M122 773H1798V946H122Z" fill="#f6e7db"/>
    <Trace d="M151 863 H1675 Q1745 863 1745 815 V773" p={go(f,419,479)} width={4}/>
    {trainingSteps.map(({en,zh,x,at})=><g key={en} opacity={go(f,at,at+12)}>
      <text x={x} y="826" fontSize="24" fontWeight="750">{en}</text>
      <circle cx={x+8} cy="863" r="7" fill={orange}/>
      <text x={x} y="910" fontSize="19" fill={brown}>{zh}</text>
    </g>)}
    <g opacity={go(f,472,490)}>
      <path d="M1745 773 V748 Q1745 727 1721 727 H1140 Q1100 727 1100 717 V592" fill="none"
        pathLength="1" stroke={orange} strokeWidth="4" strokeDasharray={`${go(f,476,502)} 1`}/>
      <text x="1157" y="720" fontSize="22" fontWeight="750" fill={orange}>CLIPPED PPO UPDATE · 限制策略更新幅度</text>
    </g>
  </g>;
}
function Unified({f}: {f:number}) {
  const actor=go(f,286,322)*fade(f,352,369);
  const critic=go(f,351,385)*fade(f,401,419);
  const trained=go(f,503,528);
  const result=go(f,536,565);
  const portrait=go(f,546,569);
  const lanes=fade(f,538,569);
  const task=go(f,549,569);
  const stateOpacity=fade(f,542,564);
  const current=go(f,513,532);
  const robotX=mix(1379,1412,portrait);
  const robotY=mix(443,540,portrait);
  const graphOpacity=mix(1,.28,portrait);
  const lens=actor+critic;
  const signal=go(f,513,545);
  const signalX=mix(385,1379,signal);
  const signalY=mix(546,443,go(f,534,545));
  return <>
    <g opacity={1-trained}><Words x={126} y={211} en="Inside the PPO network" zh="同一狀態，兩個訓練分支" size={62}/></g>
    <g opacity={trained}><Words x={126} y={211}
      en={f<551?"Trained PPO Policy":"Intelligent Task Assignment"}
      zh={f<551?"實際派工｜使用已訓練的策略":"智慧任務指派完成"} size={62}/></g>
    <g opacity={graphOpacity} transform={`translate(${-23*lens} ${-22*actor-40*critic}) scale(${1+.038*lens})`}>
      <rect x="447" y="343" width="710" height="380" rx="31" fill="#fff2e8" stroke={hair} strokeWidth="2"/>
      <text x="474" y="318" fontSize="22" fill={brown}>PPO NETWORK · 概念示意</text>
      <NetworkMesh f={f}/>
    </g>
    <g opacity={stateOpacity}>
      <text x="126" y="421" fontSize="42" fontWeight="800">{f<512?"98D State":"Current State"}</text>
      <text x="129" y="459" fontSize="25" fill={brown}>{f<512?"狀態輸入":"目前狀態"}</text>
      {Array.from({length:98},(_,i)=><rect key={i} x={mix(350+i%7*7,129+i%14*18,go(f,240,257))} y={mix(435+Math.floor(i/7)*10,496+Math.floor(i/14)*24,go(f,240,257))}
        width={mix(5,13,go(f,240,257))} height={mix(8,17,go(f,240,257))} fill={featureColors[featureIndex(i)]} rx="2"/>)}
      <Trace d="M380 546 H514" p={Math.max(go(f,248,272),current)} width={5}/>
    </g>
    <g opacity={lanes}>
      <path d="M1091 546 C1170 546 1173 443 1260 443" fill="none" stroke={actor>.2||trained>.65?orange:hair} strokeWidth={5+3*actor}/>
      <path d="M1091 546 C1170 546 1173 645 1260 645" fill="none" stroke={critic>.2?orange:hair} strokeWidth={5+3*critic} opacity={1-trained}/>
      <g opacity={1-trained}>
        <rect x="1232" y="328" width="555" height="191" rx="26" fill={mix(0,1,actor)>.25?peach:"#f6eae1"} stroke={actor>.25?orange:hair} strokeWidth="3"/>
        <g transform={`translate(${-13*actor} ${-12*actor}) scale(${1+.012*actor})`}>
          <Words x={1260} y={373} en="Actor · Policy Output" zh="策略輸出｜選擇合格動作" size={34}/>
        </g>
        <circle cx="1597" cy="443" r="28" fill={white}/><Robot x={1597} y={443} s={.60}/>
        <text x="1634" y="451" fontSize="28" fontWeight="750">M02</text>
      </g>
      <g opacity={1-trained}>
        <rect x="1232" y="556" width="555" height="171" rx="26" fill={critic>.25?peach:"#f6eae1"} stroke={critic>.25?orange:hair} strokeWidth="3"/>
        <g transform={`translate(${-13*critic} ${-13*critic}) scale(${1+.012*critic})`}>
          <Words x={1260} y={600} en="Critic · State Value Estimate" zh="狀態價值估計｜支援訓練" size={32}/>
        </g>
        <path d="M1270 687l22-21 17 12 30-30 25 12" fill="none" stroke={orange} strokeWidth="4" strokeLinecap="round"/>
        <text x="1390" y="680" fontSize="21" fill={brown}>Expected future return</text>
      </g>
      <g opacity={trained}>
        <text x="1260" y="372" fontSize="31" fontWeight="750">Actor · Eligible action</text>
        <text x="1260" y="402" fontSize="21" fill={brown}>示範選擇結果</text>
      </g>
    </g>
    {f>=513&&f<547&&<circle cx={signalX} cy={signalY} r="9" fill={orange} stroke={white} strokeWidth="3" opacity={fade(f,544,547)}/>}
    <circle cx={robotX} cy={robotY} r={mix(mix(28,42,result),158,portrait)} fill={mix(0,1,result)>.1?peach:white} stroke={orange} strokeWidth={mix(0,4,result)}/>
    <Robot x={robotX} y={robotY} s={mix(mix(.60,.86,result),3.25,portrait)}/>
    <g opacity={lanes}>
      <text x="1419" y="452" fontSize="28" fontWeight="750">{demo.robotId}</text>
    </g>
    {f>=418&&f<523&&<TrainingPath f={f}/>}
    <g opacity={task}>
      <path d="M126 380 H626 L671 425 V767 H126Z" fill={taskFill}/>
      <text x="167" y="536" fontSize="79" fontWeight="800" fill={white}>Task {demo.taskCode}</text>
      <text x="172" y="631" fontSize="41" fontWeight="600" fill="#ffc5a9">Medication Delivery</text>
      <text x="174" y="692" fontSize="30" fill={white}>Pharmacy → Ward A</text>
      <text x="1412" y="765" textAnchor="middle" fontSize="61" fontWeight="800">Assigned Robot {demo.robotId}</text>
      <text x="1412" y="818" textAnchor="middle" fontSize="27" fill={brown}>示範指派 · DEMO ASSIGNMENT</text>
    </g>
  </>;
}

export const PPOSchedulingPrototypeV8 = () => {
  const f=useCurrentFrame();
  const caption=captions.find(({from,to})=>f>=from&&f<to);
  return <AbsoluteFill style={{background:white,fontFamily:"Inter, Arial, Noto Sans CJK TC, sans-serif"}}>
    <svg width="1920" height="1080" fill={ink}>
      {f<60?<Intro f={f}/>:f<150?<Fleet f={f}/>:f<240?<State f={f}/>:<Unified f={f}/>}
    </svg>
    <div style={{position:"absolute",left:126,top:58,display:"flex",alignItems:"center",gap:10,color:ink,fontSize:32,fontWeight:750}}>
      <Img src={staticFile("dashboard-v2/brand-mark.svg")} style={{width:45,height:37}} alt=""/><span>Medi<span style={{color:orange}}>Sync</span></span>
    </div>
    {caption&&<div style={{position:"absolute",alignSelf:"center",bottom:43,background:ink,color:white,fontSize:32,borderRadius:8,padding:"9px 22px"}}>{caption.text}</div>}
    <Audio src={staticFile("ppo-v8/voice.wav")}/>
    <Audio src={staticFile("ppo-v8/score.wav")}/>
  </AbsoluteFill>;
};
