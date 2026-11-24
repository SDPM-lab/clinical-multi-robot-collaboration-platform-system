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
function Intro({f}: {f:number}) {
  const reveal=go(f,23,54);
  return <g>
    {"PPO".split("").map((letter,i)=>{
      const p=go(f,2+i*4,27+i*4);
      return <text key={i} x={250+i*373} y={586+(1-p)*(i===1?155:-117)} fill={orange} fontSize={480*mix(.69,1,p)}
        fontWeight="800" opacity={mix(.09,1,p)}>{letter}</text>;
    })}
    <g clipPath="url(#v6-title)">
      <Words x={264} y={710} en="Proximal Policy Optimization" zh="近端策略最佳化" size={64}/>
      <text x="266" y="842" fill={brown} fontSize="33">Reinforcement Learning for Robot Scheduling</text>
    </g>
    <defs><clipPath id="v6-title"><rect x="245" y="642" width="1420" height={235*reveal}/></clipPath></defs>
  </g>;
}
function Fleet({f}: {f:number}) {
  const task=go(f,103,124);
  const filter=go(f,131,158);
  return <>
    <Words x={126} y={229} en="7 Robots in the Fleet" zh="七台異質機器人" size={65}/>
    {demo.robots.map((robot,i)=>{
      const show=go(f,77+i,97+i);
      const x=225+i*245;
      const y=493+(i%2)*36;
      const eligible=robot.eligible;
      const label=eligible?"Eligible":robot.capabilityMatch?"Unavailable":"Mismatch";
      return <g key={robot.id} opacity={show} transform={`translate(${x} ${y})`}>
        <circle cy={eligible ? -19*filter : 11*filter} r={mix(28,80,show)} fill={eligible ? peach : "#f1e7e0"} stroke={eligible && filter>.5 ? orange : hair} strokeWidth="4" opacity={eligible?1:1-.48*filter}/>
        <g transform={`translate(0 ${eligible ? -19*filter : 11*filter})`} opacity={eligible?1:1-.35*filter}><Robot x={0} y={0} s={1.35} fg={eligible?"#a93710":brown}/></g>
        <text y="124" textAnchor="middle" fontSize="43" fontWeight="750" fill={ink}>{robot.id}</text>
        <text y="168" textAnchor="middle" fontSize="24" fill={eligible?"#9f3510":brown} opacity={filter}>{label}</text>
        {!eligible && robot.capabilityMatch && <text y="200" textAnchor="middle" fontSize="20" fill={brown} opacity={filter}>Charging</text>}
      </g>;
    })}
    <g clipPath="url(#v6-task)">
      <path d="M126 782 H1758 L1794 818 V901 H126Z" fill={ink}/>
      <text x="163" y="855" fill="#ffad88" fontSize="35" fontWeight="750">T0002 · HIGH PRIORITY</text>
      <text x="679" y="855" fill={white} fontSize="34">Medication delivery · Pharmacy → Ward A</text>
    </g>
    <defs><clipPath id="v6-task"><rect x="126" y="782" width={1668*task} height="125"/></clipPath></defs>
  </>;
}
const groups=[
  {x:150,n:41,c:orange,en:"Task information",zh:"任務資訊"},
  {x:730,n:56,c:"#a77360",en:"Robot fleet state",zh:"車隊狀態"},
  {x:1310,n:1,c:ink,en:"System workload",zh:"整體負載"},
];
function State({f}: {f:number}) {
  const pack=go(f,216,251);
  const name=go(f,223,252);
  return <>
    {groups.map(({x,c,en,zh},i)=>{
      const arrive=go(f,180+i*4,197+i*4);
      return <g key={en} opacity={arrive*(1-.13*pack)} transform={`translate(0 ${32*(1-arrive)})`}>
        <Words x={x} y={295} en={en} zh={zh} size={43}/>
        {i===0 && <g fill={peach} stroke={c} strokeWidth="2"><path d={`M${x} 417 h247 l24 25 -24 25 h-247Z`}/><path d={`M${x} 488 h335 l24 25 -24 25 h-335Z`}/>
          <text x={x+18} y="450" fill={ink} stroke="none" fontSize="26">High priority</text><text x={x+18} y="521" fill={ink} stroke="none" fontSize="26">Pharmacy → Ward A</text></g>}
        {i===1 && <g>{[0,1,2,3,4].map(j=><g key={j}><Robot x={x+35+j*87} y={461} s={.78} fg={c}/><rect x={x+11+j*87} y="509" width={25+(j%3)*9} height="9" rx="4" fill={c}/></g>)}</g>}
        {i===2 && <g stroke={c} fill="none" strokeWidth="6"><path d={`M${x} 528 h388`}/>{[40,91,57,28,70].map((v,j)=><path key={j} d={`M${x+27+j*75} 525 v-${v}`} stroke={j===1?orange:c} strokeWidth="27"/>)}</g>}
      </g>;
    })}
    {Array.from({length:98},(_,i)=>{
      const g=i<41?0:i<97?1:2;
      const j=i-[0,41,97][g];
      return <rect key={i} x={mix(groups[g].x+j%14*25,150+i*16.5,pack)} y={mix(609+Math.floor(j/14)*22,673,pack)}
        width={mix(g===2?30:12,12,pack)} height={mix(10,57,pack)} fill={groups[g].c} rx="2"
        opacity={go(f,202+g*3,220+g*3)}/>;
    })}
    <g opacity={name}><Words x={147} y={835} en="98-Dimensional State" zh="98 維狀態輸入" size={70}/></g>
  </>;
}
const layers=[[420,[422,514,606]],[697,[365,460,555,650]],[983,[422,514,606]],[1291,[469,559]]] as const;
function Network({f,update=0}: {f:number;update?:number}) {
  return <>
    {layers.slice(0,-1).flatMap(([x,ys],i)=>ys.flatMap((y,j)=>layers[i+1][1].map((ty,k)=>{
      const next=layers[i+1][0];
      const p=go(f,275+i*9+j*2,291+i*9+j*2);
      const active=(j+k+i)%4===0;
      return <path key={`${x}-${y}-${ty}`} d={`M${x} ${y}L${next} ${ty}`} fill="none"
        stroke={active && p>.5?orange:hair} strokeWidth={active?mix(5,2,update):2} opacity={active?mix(.5,.91,p):.78}/>;
    })))}
    {layers.map(([x,ys],i)=>ys.map((y,j)=>{
      const p=go(f,273+i*8+j*2,284+i*8+j*2);
      return <circle key={`${x}-${y}`} cx={x} cy={y} r={mix(18,28,p)} fill={p>.72 && (i+j)%3===0?orange:peach} stroke={orange} strokeWidth="3"/>;
    }))}
  </>;
}

function Input({f}: {f:number}) {
  const push=go(f,274,309);
  return <>
    <Words x={126} y={231} en="Inside the PPO network" zh="98 維狀態進入策略網路"/>
    <g transform={`translate(${-94*push} ${-67*push}) scale(${1+.19*push})`}>
      <text x="139" y="475" fontSize="40" fontWeight="800" fill={ink}>98D</text>
      <Trace d="M139 515 H420" p={go(f,270,294)}/>
      <Network f={f}/>
    </g>
  </>;
}

function Focus({f,actor}: {f:number;actor:boolean}) {
  const p=go(f,actor?312:338,actor?332:357);
  return <>
    <Words x={126} y={234} en={actor?"Actor":"Critic"} zh={actor?"決定採取什麼動作":"估計目前狀態的價值"} size={86}/>
    <circle cx="721" cy="550" r="175" fill={peach}/>
    {actor ? <>
      <Trace d="M290 550 H721 Q850 550 970 426 H1380" p={p}/>
      <Trace d="M721 550 H1380" p={0}/>
      <Trace d="M721 550 Q850 550 970 674 H1380" p={0}/>
      <circle cx="721" cy="550" r="34" fill={orange}/>
      <circle cx="1380" cy="426" r="71" fill={peach} stroke={orange} strokeWidth="4" opacity={p}/>
      <g opacity={p}><Robot x={1380} y={426} s={1.25}/><text x="1470" y="437" fill={ink} fontSize="35" fontWeight="700">Action</text></g>
    </> : <>
      <Trace d="M290 550 H721 H1380" p={p}/>
      <circle cx="721" cy="550" r="34" fill={orange}/>
      <g opacity={p}>
        <path d="M1190 550 H1530" stroke={hair} strokeWidth="22" strokeLinecap="round"/>
        <path d="M1190 550 H1380" stroke={orange} strokeWidth="22" strokeLinecap="round"/>
        <path d="M1380 524v52" stroke={ink} strokeWidth="5" strokeLinecap="round"/>
      </g>
      <text x="1177" y="674" fill={ink} fontSize="42" fontWeight="700">State value</text>
    </>}
  </>;
}

function Feedback({f}: {f:number}) {
  const feedback=go(f,362,387);
  const update=go(f,384,415);
  return <>
    <Words x={126} y={239} en={f<389?"Reward feedback":"Policy update"} zh={f<389?"環境給出獎勵回饋":"從訓練經驗更新策略"} size={65}/>
    <g opacity={1-update}>
      <Trace d="M352 545 H1574" p={feedback}/>
      {["Action","Environment","Reward"].map((word,i)=><g key={word} opacity={go(f,362+i*6,371+i*6)}>
        <circle cx={352+i*611} cy="545" r="85" fill={i===2?orange:peach}/>
        <text x={352+i*611} y="556" textAnchor="middle" fontSize={i===1?27:32} fontWeight="750" fill={i===2?white:ink}>{word}</text>
      </g>)}
    </g>
    <g opacity={update} transform="translate(206 99) scale(.86)"><Network f={f} update={update}/></g>
  </>;
}

function Inference({f}: {f:number}) {
  const switchOver=go(f,431,461);
  const routing=go(f,466,501);
  return <>
    <g opacity={1-switchOver}>
      <Words x={126} y={230} en="Offline training" zh="離線訓練"/>
      <g transform={`translate(${438*switchOver} ${256*switchOver}) scale(${mix(1,.48,switchOver)})`}><Network f={419} update={1}/></g>
    </g>
    <g clipPath="url(#v6-inference)">
      <rect width="1920" height="1080" fill={white}/>
      <Words x={126} y={231} en="Inference" zh="實際派工"/>
      <Trace d="M444 550 H1537" p={routing}/>
      <circle cx="960" cy="550" r="168" fill={ink}/>
      <text x="960" y="540" textAnchor="middle" fill={white} fontSize="41" fontWeight="750">Trained PPO</text>
      <text x="960" y="593" textAnchor="middle" fill="#ffad88" fontSize="35">Policy</text>
      <rect x="224" y="519" width="225" height="63" rx="31" fill={peach}/>
      <text x="337" y="560" textAnchor="middle" fontSize="31" fontWeight="700">Current state</text>
      <circle cx="1537" cy="550" r="85" fill={peach} stroke={orange} strokeWidth="3"/>
      <Robot x={1537} y={550} s={1.45}/>
      <text x="1537" y="685" textAnchor="middle" fontSize="32" fontWeight="700">Assignment</text>
    </g>
    <defs><clipPath id="v6-inference"><circle cx="960" cy="550" r={switchOver*1200}/></clipPath></defs>
  </>;
}

function Assignment({f}: {f:number}) {
  const hero=go(f,510,548);
  return <>
    <Words x={126} y={229} en="Intelligent Task Assignment" zh="智慧任務指派" size={67}/>
    <path d="M182 403 H678 L725 450 V722 H182Z" fill={ink}/>
    <text x="222" y="523" fontSize="73" fontWeight="800" fill={white}>Task {demo.taskCode}</text>
    <text x="229" y="625" fontSize="38" fill="#ffb193">Medication Delivery</text>
    <Trace d="M725 550 H1340" p={hero}/>
    <circle cx={mix(1537,1340,hero)} cy="550" r={mix(85,163,hero)} fill={peach} stroke={orange} strokeWidth="4"/>
    <Robot x={mix(1537,1340,hero)} y={550} s={mix(1.45,3.08,hero)}/>
    <g opacity={go(f,526,551)}>
      <text x="1340" y="805" textAnchor="middle" fontSize="66" fontWeight="800">Robot {demo.robotId}</text>
      <text x="1340" y="856" textAnchor="middle" fill={brown} fontSize="32">Assigned Robot · 示範指派</text>
    </g>
  </>;
}

export const PPOSchedulingPrototypeV6 = () => {
  const f=useCurrentFrame();
  const caption=captions.find(({from,to})=>f>=from&&f<to);
  const wipe=go(f,78,90);
  return <AbsoluteFill style={{background:white,fontFamily:"Inter, Arial, Noto Sans CJK TC, sans-serif"}}>
    <svg width="1920" height="1080" fill={ink}>
      {f<90 ? <>
        <Intro f={f}/>
        {f>=78 && <g clipPath="url(#v6-letter)"><rect width="1920" height="1080" fill={white}/><Fleet f={f}/></g>}
        <defs><clipPath id="v6-letter"><text x="0" y="0" fontSize="480" fontWeight="800"
          transform={`translate(996 586) scale(${mix(1,5,wipe)}) translate(-190 170)`}>O</text><circle cx="1174" cy="426" r={go(f,81,89)*1390}/></clipPath></defs>
      </> : f<180?<Fleet f={f}/>:f<270?<State f={f}/>:f<312?<Input f={f}/>:f<338?<Focus f={f} actor/>:f<362?<Focus f={f} actor={false}/>:f<420?<Feedback f={f}/>:f<510?<Inference f={f}/>:<Assignment f={f}/>}
    </svg>
    <div style={{position:"absolute",left:126,top:58,display:"flex",alignItems:"center",gap:10,color:ink,fontSize:32,fontWeight:750}}>
      <Img src={staticFile("dashboard-v2/brand-mark.svg")} style={{width:45,height:37}} alt=""/><span>Medi<span style={{color:orange}}>Sync</span></span>
    </div>
    {caption&&<div style={{position:"absolute",alignSelf:"center",bottom:43,background:ink,color:white,fontSize:32,borderRadius:8,padding:"9px 22px"}}>{caption.text}</div>}
    <Audio src={staticFile("ppo-v6/voice.wav")}/>
    <Audio src={staticFile("ppo-v6/score.wav")}/>
  </AbsoluteFill>;
};
