import {AbsoluteFill, Audio, Easing, Img, interpolate, staticFile, useCurrentFrame} from "remotion";
import demo from "./ppo-v9-observation.json";
import captions from "./ppo-v9-captions.json";

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
const features = [
  ["Capability","能力符合"],["Assignable","可派遣"],["Busy","忙碌"],
  ["Load","負載"],["Approach","預估接近時間"],["Tasks ahead","前方任務"],["Battery","電量"],["Battery block","電池不可用"],
];
function FeatureMatrix({f}: {f:number}) {
  const mask=go(f,180,206);
  const focus=go(f,153,178)*(1-go(f,214,233));
  return <>
    <Words x={126} y={214} en="Robot Feature Matrix" zh="七台機器人・每台八項模型特徵" size={63}/>
    <text x="1795" y="215" textAnchor="end" fontSize="32" fontWeight="750">T0002 · Medication delivery</text>
    <text x="1795" y="253" textAnchor="end" fontSize="24" fill={brown}>Pharmacy → Ward A · High priority</text>
    <rect x="122" y="316" width="1443" height="526" rx="19" fill="#f7ede5"/>
    <rect x="314" y="316" width="299" height="526" rx="14" fill={peach} opacity={focus}/>
    <text x="158" y="359" fontSize="28" fontWeight="750">Robot ID</text>
    {features.map(([en,zh],i)=><g key={en} opacity={go(f,62+i*6,80+i*6)}>
      <text x={387+i*148} y="350" textAnchor="middle" fontSize="23" fontWeight="750">{en}</text>
      <text x={387+i*148} y="380" textAnchor="middle" fontSize="18" fill={brown}>{zh}</text>
    </g>)}
    <g clipPath="url(#v9-mask)">
      <rect x="1590" y="316" width="208" height="526" rx="19" fill="#f6e3d5" stroke={hair} strokeWidth="2"/>
      <text x="1694" y="347" textAnchor="middle" fontSize="25" fontWeight="800">Action Mask</text>
      <text x="1694" y="379" textAnchor="middle" fontSize="19" fill={brown}>動作資格遮罩</text>
    </g>
    <defs><clipPath id="v9-mask"><rect x="1588" y="314" width={212*mask} height="530"/></clipPath></defs>
    {demo.robots.map((robot,i)=>{
      const y=430+i*60;
      const enabled=demo.actionMask[i];
      return <g key={robot.id}>
        <path d={`M142 ${y-29}H1542`} stroke={hair} strokeWidth="2"/>
        <g opacity={go(f,60+i*2,78+i*2)}><Robot x={166} y={y-4} s={.51}/><text x="201" y={y+6} fontSize="30" fontWeight="800">{robot.id}</text></g>
        {features.map(([label],j)=>{
          const value=demo.observation[41+i*8+j];
          const display=j===6?`${Math.round(value*100)}%`:j===3||j===4||j===5?value.toFixed(2):String(value);
          return <text key={label} x={387+j*148} y={y+6} textAnchor="middle" fontSize="29" fontWeight="700"
            fill={j<2&&focus>.5&&value===1?"#a43c16":ink} opacity={go(f,72+j*6+i,92+j*6+i)}>{display}</text>;
        })}
        <g opacity={go(f,198+i*3,212+i*3)}>
          <rect x="1640" y={y-29} width="108" height="47" rx="10" fill={enabled?orange:"#e7d5c8"}/>
          <text x="1694" y={y+5} textAnchor="middle" fontSize="32" fontWeight="850" fill={enabled?white:brown}>{Number(enabled)}</text>
        </g>
      </g>;
    })}
    <text x="128" y="903" fill={brown} fontSize="23">Load / Approach / Tasks ahead are normalized · 負載、接近時間、前方任務數已正規化</text>
    <g opacity={go(f,211,226)}>
      <text x="1774" y="870" textAnchor="end" fontSize="26" fontWeight="750" fill={orange}>1 = Eligible / Selectable</text>
      <text x="1774" y="908" textAnchor="end" fontSize="25" fill={brown}>0 = Masked / Not Selectable</text>
    </g>
  </>;
}
function StateMask({f}: {f:number}) {
  const gather=go(f,301,324);
  const enter=go(f,371,389);
  return <>
    <g opacity={1-enter}>
      <Words x={126} y={218} en="Two inputs, two roles" zh="98 維狀態與 7 位動作遮罩各自保留" size={64}/>
      <Words x={125} y={353} en="98-Dimensional Observation" zh="狀態表示｜保留所有七台" size={47}/>
      <text x="126" y="731" fontSize="30" fill={brown}>41 Task + 56 Fleet + 1 System</text>
      <text x="126" y="787" fontSize="29" fontWeight="750">State → PPO Policy</text>
      <path d="M1260 319V824" stroke={hair} strokeWidth="3"/>
      <Words x={1335} y={357} en="Action Eligibility" zh="0／1 動作限制" size={43}/>
      <text x="1335" y="730" fontSize="28" fontWeight="750">Mask → Action Selection</text>
      <text x="1335" y="777" fontSize="24" fill={brown}>限制可選動作</text>
    </g>
    {demo.observation.map((v,i)=>{
      const group=featureIndex(i);
      const blockX=group===0?127:group===1?627:1114;
      const idx=i-[0,41,97][group];
      const x=mix(mix(blockX+(idx%10)*44,128+(i%14)*73,gather),129+(i%14)*21,enter);
      const y=mix(mix(461+Math.floor(idx/10)*37,427+Math.floor(i/14)*38,gather),459+Math.floor(i/14)*26,enter);
      return <rect key={i} x={x} y={y} width={mix(60*gather+27*(1-gather),16,enter)} height={mix(28,19,enter)} rx="4"
        fill={featureColors[group]} opacity={.45+.55*v}/>;
    })}
    {demo.actionMask.map((ok,i)=><g key={i} opacity={1-enter}>
      <rect x={1336+i*59} y="487" width="51" height="67" rx="8" fill={ok?orange:"#e7d5c8"}/>
      <text x={1361+i*59} y="529" textAnchor="middle" fontSize="30" fontWeight="850" fill={ok?white:brown}>{Number(ok)}</text>
    </g>)}
  </>;
}
const layers=[
  {x:542,ys:[453,539,625]},
  {x:751,ys:[397,489,581,673]},
  {x:973,ys:[453,539,625]},
  {x:1112,ys:[539]},
];
const rollout=[
  ["Environment feedback","環境回饋",540,142],
  ["Reward","獎勵訊號",558,495],
  ["Training experience","收集經驗",572,707],
  ["Advantage estimation","估計優勢",586,1050],
  ["Clipped PPO update","限制更新幅度",609,1390],
] as const;
function Network({f}: {f:number}) {
  const actor=go(f,429,455)*(1-go(f,475,492));
  const critic=go(f,481,504)*(1-go(f,524,541));
  const update=go(f,604,648);
  const fitted=go(f,648,669);
  const final=go(f,672,695);
  const showTraining=go(f,537,551)*(1-go(f,651,668));
  const nodesAlpha=mix(1,.23,final);
  const hubX=mix(1370,1414,final);
  const hubY=mix(456,554,final);
  return <>
    <g opacity={1-fitted}><Words x={126} y={218} en="Inside the PPO network" zh="狀態輸入、策略輸出與價值估計" size={63}/></g>
    <g opacity={fitted}><Words x={126} y={218} en={f<679?"Trained PPO Policy":"Intelligent Task Assignment"}
      zh={f<679?"使用已訓練的策略派工":"智慧任務指派完成"} size={63}/></g>
    <g opacity={nodesAlpha}>
      <text x="128" y="407" fontSize="43" fontWeight="800">{f<660?"98D State Input":"Current State"}</text>
      {demo.observation.map((v,i)=><rect key={i} x={129+(i%14)*21} y={459+Math.floor(i/14)*26}
        width="16" height="19" rx="4" fill={featureColors[featureIndex(i)]} opacity={.45+.55*v}/>)}
      <text x="129" y="698" fontSize="23" fontWeight="800">ACTION MASK</text>
      {demo.actionMask.map((ok,i)=><g key={i}>
        <rect x={126+i*43} y="709" width="35" height="40" rx="7" fill={ok?orange:"#eadcd1"}/>
        <text x={143+i*43} y="738" textAnchor="middle" fontSize="24" fontWeight="800" fill={ok?white:brown}>{Number(ok)}</text>
      </g>)}
      <Trace d="M416 540H523" p={go(f,390,414)} width={5}/>
      <rect x="500" y="341" width="666" height="378" rx="29" fill="#fff0e5" stroke={hair} strokeWidth="2"/>
      <text x="508" y="321" fontSize="23" fill={brown}>PPO NETWORK · 概念示意</text>
      {layers.slice(0,-1).flatMap(({x,ys},i)=>ys.slice(0,3).flatMap((y,j)=>{
        const next=layers[i+1]; const end=next.ys[j%next.ys.length];
        const alt=next.ys[(j+1)%next.ys.length];
        const d=`M${x} ${y} Q${(x+next.x)/2} ${y} ${next.x} ${end}`;
        return [<path key={`${x}-${y}`} d={`M${x} ${y} Q${(x+next.x)/2} ${y} ${next.x} ${alt}`} stroke={hair} strokeWidth="3" fill="none"/>,
          <path key={d} d={d} pathLength="1" stroke={j===i%3?orange:"#d4ad9a"} strokeWidth={j===i%3?mix(5,3,update):3}
            fill="none" strokeDasharray={`${go(f,396+i*9+j,421+i*9+j)} 1`}/>];
      }))}
      {layers.flatMap(({x,ys},i)=>ys.map((y,j)=><circle key={`${x}-${y}`} cx={x} cy={y} r={22+i*2}
        fill={(i+j)%3===0?orange:peach} stroke={orange} strokeWidth="2" opacity={mix(.45,1,go(f,393+i*9+j,414+i*9+j))}/>))}
      <path d="M1112 539 Q1197 530 1243 455" stroke={actor>.25||fitted>.5?orange:hair} strokeWidth={4+3*actor} fill="none"/>
      <path d="M1112 539 Q1196 548 1243 652" stroke={critic>.25?orange:hair} strokeWidth={4+3*critic} fill="none" opacity={1-fitted}/>
      <path d="M424 728 H1139 Q1193 728 1193 679 V502 H1239" stroke={orange} strokeWidth="2" strokeDasharray="6 8" fill="none" opacity={go(f,437,461)*.72}/>
    </g>
    <g opacity={1-final}>
      <rect x="1234" y="341" width="556" height="188" rx="24" fill={actor>.26?peach:"#f8eee6"} stroke={actor>.26?orange:hair} strokeWidth="3"/>
      <Words x={1266} y={389} en={f<664?"Actor · Policy Output":"Actor · Demo Selected Action"} zh="策略輸出｜在合格動作中選擇" size={34}/>
      <text x="1411" y="467" fontSize="33" fontWeight="800">M01</text>
      <g opacity={1-fitted}><Robot x={1586} y={456} s={.66}/><text x="1621" y="467" fontSize="33" fontWeight="800">M02</text></g>
      <g opacity={go(f,443,464)*(1-fitted)}>
        <text x="1266" y="507" fontSize="19" fill={brown}>LOGITS</text>
        {demo.robots.map((robot,i)=><g key={robot.id} opacity={demo.actionMask[i]?1:.38}>
          <text x={1370+i*55} y="507" fontSize="18" fontWeight="750" textAnchor="middle">{robot.id}</text>
          {!demo.actionMask[i]&&<path d={`M${1351+i*55} 501h38`} stroke={brown} strokeWidth="2"/>}
        </g>)}
      </g>
      <g opacity={1-fitted}>
        <rect x="1234" y="555" width="556" height="163" rx="24" fill={critic>.26?peach:"#f8eee6"} stroke={critic>.26?orange:hair} strokeWidth="3"/>
        <Words x={1266} y={610} en="Critic · State Value Estimate" zh="估計狀態的預期未來回報" size={33}/>
        <path d="M1268 681l18-13 21 5 31-19 18 5" stroke={orange} fill="none" strokeWidth="3"/>
      </g>
    </g>
    <circle cx={hubX} cy={hubY} r={mix(26,143,final)} fill={mix(0,1,final)>.05?peach:white} stroke={orange} strokeWidth={3*final}/>
    <Robot x={hubX} y={hubY} s={mix(.66,2.93,final)}/>
    <g opacity={showTraining}>
      <rect x="124" y="772" width="1673" height="161" rx="17" fill="#f3e1d4"/>
      <Trace d="M152 850 H1670" p={go(f,541,635)} width={4}/>
      {rollout.map(([en,zh,start,x])=><g key={en} opacity={go(f,start,start+15)}>
        <text x={x} y="822" fontSize="23" fontWeight="750">{en}</text>
        <circle cx={x+12} cy="850" r="7" fill={orange}/>
        <text x={x} y="892" fontSize="21" fill={brown}>{zh}</text>
      </g>)}
      <path d="M1634 850 Q1744 850 1744 796 Q1744 754 1700 754 H1165 Q1134 754 1134 714"
        fill="none" pathLength="1" stroke={orange} strokeWidth="4" strokeDasharray={`${update} 1`}/>
    </g>
    <g opacity={final}>
      <path d="M124 359 H626 L673 410 V771 H124Z" fill={taskFill}/>
      <text x="165" y="526" fontSize="82" fontWeight="850" fill={white}>Task {demo.taskCode}</text>
      <text x="171" y="622" fontSize="43" fill="#ffc3a6">Medication Delivery</text>
      <text x="1414" y="780" textAnchor="middle" fontSize="58" fontWeight="800">Assigned Robot {demo.robotId}</text>
      <text x="1414" y="827" textAnchor="middle" fontSize="26" fill={brown}>DEMO ASSIGNMENT · 示範指派</text>
    </g>
  </>;
}

export const PPOSchedulingPrototypeV9 = () => {
  const f=useCurrentFrame();
  const caption=captions.find(({from,to})=>f>=from&&f<to);
  return <AbsoluteFill style={{background:white,fontFamily:"Inter, Arial, Noto Sans CJK TC, sans-serif"}}>
    <svg width="1920" height="1080" fill={ink}>
      {f<60?<Intro f={f}/>:f<300?<FeatureMatrix f={f}/>:f<390?<StateMask f={f}/>:<Network f={f}/>}
    </svg>
    <div style={{position:"absolute",left:126,top:58,display:"flex",alignItems:"center",gap:10,color:ink,fontSize:32,fontWeight:750}}>
      <Img src={staticFile("dashboard-v2/brand-mark.svg")} style={{width:45,height:37}} alt=""/><span>Medi<span style={{color:orange}}>Sync</span></span>
    </div>
    {caption&&<div style={{position:"absolute",alignSelf:"center",bottom:43,background:ink,color:white,fontSize:32,borderRadius:8,padding:"9px 22px"}}>{caption.text}</div>}
    <Audio src={staticFile("ppo-v9/voice.wav")}/>
    <Audio src={staticFile("ppo-v9/score.wav")}/>
  </AbsoluteFill>;
};
