import { AbsoluteFill, Audio, Easing, Img, interpolate, staticFile, useCurrentFrame } from "remotion";
import demo from "./ppo-scheduling-demo.json";
import captions from "./ppo-v5-captions.json";

const ink = "#211a17";
const paper = "#fffaf4";
const orange = "#e84d18";
const warm = "#ff976c";
const muted = "#72645b";
const line = "#e2d5ca";
const ramp = (f: number, a: number, b: number) => interpolate(f, [a,b], [0,1], {
  extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.bezier(.34,0,.25,1),
});
const mix = (a: number,b: number,t: number) => a+(b-a)*t;
const Word = ({x,y,size = 31,fill = ink,weight = 600, children}: {
  x: number; y: number; size?: number; fill?: string; weight?: number; children: React.ReactNode;
}) => <text x={x} y={y} fontSize={size} fill={fill} fontWeight={weight}>{children}</text>;

function Intro({f}: {f:number}) {
  const title = ramp(f,14,42);
  const chinese = ramp(f,32,57);
  return <>
    <g opacity=".6" stroke={line} strokeWidth="2" fill="none">
      {Array.from({length: 6}, (_,i) => <path key={i} d={`M ${1150+i*75} 210 V ${410+i*54} H 1790`} pathLength="1"
        strokeDasharray={`${ramp(f,16+i*2,59+i*2)} 1`}/>)}
    </g>
    {Array.from({length: 6},(_,i)=><circle key={i} cx={1150+i*75} cy={410+i*54} r="7" fill={orange} opacity={.46*ramp(f,28+i*3,45+i*3)}/>)}
    {["P","P","O"].map((letter,i)=>{
      const p = ramp(f,i*3,25+i*3);
      return <text key={i} x={216+i*208} y="550" fontWeight="800" fontSize="304" fill={orange}
        transform={`translate(${(1-p)*24} ${(1-p)*(i%2 ? 100 : -75)}) scale(${mix(.86,1,p)} 1)`} opacity={mix(.2,1,p)}>{letter}</text>;
    })}
    <g clipPath="url(#v5IntroEn)"><Word x={230} y={649} size={68} weight={750}>Proximal Policy Optimization</Word></g>
    <g clipPath="url(#v5IntroZh)" transform={`translate(${30*(1-chinese)} 0)`}>
      <Word x={232} y={725} size={40} fill={muted}>近端策略優化｜強化學習調度核心</Word>
    </g>
    <defs>
      <clipPath id="v5IntroEn"><rect x="222" y="570" width={1120*title} height="108"/></clipPath>
      <clipPath id="v5IntroZh"><rect x="222" y="674" width={720*chinese} height="70"/></clipPath>
    </defs>
  </>;
}

function Filter({f}: {f:number}) {
  const intro = ramp(f,75,91);
  const key = ramp(f,100,127);
  return <>
    <Word x={126} y={222} size={72} weight={750}>Which robot can take the task?</Word>
    <Word x={130} y={274} size={31} fill={muted}>Capability and availability determine eligibility</Word>
    <g opacity={intro}>
      <path d="M126 359 H704 L752 407 V801 H126Z" fill={ink}/>
      <Word x={173} y={439} fill={warm} size={34}>TASK REQUEST</Word>
      <Word x={173} y={559} fill={paper} size={108} weight={800}>{demo.taskCode}</Word>
      <Word x={177} y={629} fill={paper} size={43}>Medication delivery</Word>
      <Word x={177} y={682} fill="#decac0" size={36}>Pharmacy → Ward A</Word>
      <Word x={177} y={750} fill={warm} size={31}>HIGH PRIORITY</Word>
    </g>
    <Word x={844} y={350} size={25} fill={muted} weight={700}>ROBOT</Word>
    <Word x={1139} y={350} size={25} fill={muted} weight={700}>SCREENING RESULT</Word>
    {demo.robots.map((robot,i)=>{
      const y = 414+i*63;
      const show = ramp(f,75+i*2,90+i*2);
      const shift = robot.eligible ? -19*key : 17*key;
      const status = robot.eligible ? "Eligible" : robot.capabilityMatch ? "Charging · unavailable" : "Capability mismatch";
      const text = robot.eligible ? "#a9320e" : muted;
      return <g key={robot.id} transform={`translate(${shift} 0)`} opacity={show}>
        <path d={`M834 ${y-39} H1748 L1777 ${y-9} L1748 ${y+11} H834Z`}
          fill={robot.eligible && f>=109 ? "#ffe1d1" : "#f3eae1"} opacity={robot.eligible ? 1 : mix(1,.53,key)}/>
        <path d={`M858 ${y-24} l10 10 -10 10 -10 -10Z`} fill={robot.eligible ? orange : "#a99a8e"}/>
        <Word x={888} y={y-4} size={33} fill={robot.eligible ? text : ink} weight={750}>{robot.id}</Word>
        <g opacity={key}><Word x={1140} y={y-4} size={29} fill={text}>{status}</Word></g>
        {robot.eligible && <path d={`M1699 ${y-13} l8 8 17 -18`} stroke={orange} strokeWidth="4" fill="none" opacity={key}/>}
      </g>;
    })}
  </>;
}

const featureGroup = [
  {title:"Task", description:"Type · Priority · Locations", count:41, x:160, color:orange},
  {title:"Fleet", description:"Capability · Availability · Battery", count:56, x:720, color:"#875545"},
  {title:"System", description:"Fleet load imbalance", count:1, x:1320, color:ink},
];
function State({f}: {f:number}) {
  const join = ramp(f,174,214);
  const reveal = ramp(f,192,218);
  return <>
    <Word x={126} y={211} size={69} weight={750}>Encode the current state</Word>
    {featureGroup.map(({title,description,count,x,color},group)=>{
      const p = ramp(f,150+group*3,163+group*3);
      return <g key={title} transform={`translate(${(1-p)*(group-1)*125} ${(1-p)*56})`} opacity={p*(1-.17*join)}>
        <path d={`M${x} 357 h405`} stroke={color} strokeWidth="4"/>
        <Word x={x} y={431} size={61} fill={color} weight={750}>{title}</Word>
        <Word x={x} y={481} size={29} fill={muted}>{description}</Word>
        <Word x={x} y={551} size={32} fill={color}>{count} {count===1 ? "feature" : "features"}</Word>
      </g>;
    })}
    {Array.from({length:98},(_,i)=>{
      const group = i<41 ? 0 : i<97 ? 1 : 2;
      const index = i-[0,41,97][group];
      const {x,color} = featureGroup[group];
      const sx = x + index%14*25;
      const sy = 625 + Math.floor(index/14)*26;
      return <rect key={i} x={mix(sx,167+i*16.3,join)} y={mix(sy,653,join)}
        width={mix(group===2 ? 75 : 15,12,join)} height={mix(13+group*10,56,join)} rx={mix(5,2,join)} fill={color} opacity={ramp(f,151+group*3,166+group*3)}/>;
    })}
    <g opacity={reveal}>
      <Word x={166} y={789} size={78} weight={800}>98-D State Vector</Word>
      <Word x={172} y={854} size={34} fill={muted}>由任務、車隊與系統資訊共同組成</Word>
      <Word x={1300} y={788} size={29} fill={muted}>INPUT TO THE POLICY</Word>
    </g>
  </>;
}

const columns = [
  {x:510, ys:[390,463,536,609]},
  {x:670, ys:[350,422,494,566,638]},
  {x:835, ys:[390,463,536,609]},
];
const graphEdges = columns.slice(0,-1).flatMap(({x,ys},i)=>ys.flatMap(y=>columns[i+1].ys.map(to=>({
  x,y,toX:columns[i+1].x,to,
}))));
function Flow({d,f,a,b,color=warm,width=4}: {d:string;f:number;a:number;b:number;color?:string;width?:number}) {
  return <><path d={d} fill="none" stroke="#63483c" strokeWidth={width}/>
    <path d={d} fill="none" stroke={color} strokeWidth={width} pathLength="1" strokeLinecap="round" strokeDasharray={`${ramp(f,a,b)} 1`}/></>;
}
function Learning({f}: {f:number}) {
  const actor = ramp(f,259,282);
  const critic = ramp(f,270,294);
  const reward = ramp(f,300,327);
  const update = ramp(f,336,363);
  const net = ramp(f,248,274);
  return <>
    <rect width="1920" height="1080" fill={ink}/>
    <Word x={126} y={173} size={27} fill={warm} weight={750}>OFFLINE TRAINING</Word>
    <Word x={124} y={250} size={69} fill={paper} weight={750}>Learn from experience</Word>
    <Word x={134} y={377} size={42} fill={paper} weight={750}>98D state</Word>
    <Word x={135} y={422} size={29} fill="#e0bfb0">狀態輸入</Word>
    <Flow d="M138 468 H410 Q438 468 461 495 H490" f={f} a={240} b={256}/>
    {Array.from({length:14},(_,i)=><rect key={i} x={138+i*17} y="488" width="11" height="35" rx="3" fill={i<6 ? warm : "#a57d6c"}/>)}
    <Word x={477} y={320} size={31} fill={paper}>Neural network · 策略網路</Word>
    {graphEdges.map(({x,y,toX,to},i)=><path key={i} d={`M${x} ${y} L${toX} ${to}`} stroke={i%6===0 ? "#f59870" : "#a67059"} strokeWidth={mix(1.2,i%6===0 ? 3.8 : 1.7,update)} opacity={.18+.49*net}/>)}
    {columns.map(({x,ys},i)=>ys.map((y,j)=><circle key={`${x}-${y}`} cx={x} cy={y} r={mix(9,14,ramp(f,247+i*5,259+i*5))}
      fill={(j+i)%3===0 ? warm : "#936e5e"} stroke="#f3bfab" strokeWidth="1.5"/>))}
    <Flow d="M848 462 H946 Q975 462 1000 422 H1051" f={f} a={257} b={282}/>
    <Flow d="M848 535 H944 Q973 535 1000 599 H1051" f={f} a={267} b={294} color="#f0c3a8"/>
    <g opacity={actor}>
      <Word x={1080} y={407} size={49} fill={paper} weight={750}>Actor</Word>
      <Word x={1083} y={453} size={29} fill="#efc6b4">Selects an eligible action</Word>
      <path d="M1482 423 h86" stroke={warm} strokeWidth="3"/>
      <Word x={1590} y={434} size={32} fill={warm}>Action</Word>
    </g>
    <g opacity={critic}>
      <Word x={1080} y={590} size={49} fill={paper} weight={750}>Critic</Word>
      <Word x={1083} y={635} size={29} fill="#efc6b4">Estimates state value</Word>
    </g>
    <Flow d="M1700 446 Q1741 451 1741 501 V701 Q1741 725 1712 725 H850" f={f} a={291} b={333}/>
    <g opacity={reward}>
      <Word x={1336} y={786} size={34} fill={warm}>Reward · 獎勵回饋</Word>
      <Word x={1336} y={821} size={25} fill="#efc6b4">From environment outcomes</Word>
    </g>
    <Flow d="M845 725 H696 Q670 725 670 692 V655" f={f} a={331} b={365}/>
    <g opacity={update}>
      <Word x={482} y={786} size={34} fill={warm}>Policy update · 策略更新</Word>
      <Word x={482} y={821} size={25} fill="#efc6b4">From collected experience</Word>
    </g>
  </>;
}

function Decision({f}: {f:number}) {
  const iris = ramp(f,390,410);
  const p = ramp(f,425,475);
  const lock = ramp(f,472,491);
  return <>
    <Learning f={389}/>
    <g clipPath="url(#v5Inference)">
      <rect width="1920" height="1080" fill={paper}/>
      <Word x={126} y={214} size={29} fill={orange} weight={800}>INFERENCE · 實際排程</Word>
      <Word x={126} y={292} size={67} weight={750}>Intelligent assignment</Word>
      <g opacity={1-p}>
        <Word x={358} y={563} size={49}>Current state</Word>
        <path d="M702 545 h132 m-20 -13 20 13 -20 13" fill="none" stroke={orange} strokeWidth="4"/>
      </g>
      <path d="M949 442 H1354 L1413 499 V610 L1354 667 H949 L890 610 V499Z" fill={ink}
        transform={`translate(${-96*p} ${-21*p})`}/>
      <g opacity={1-p}>
        <Word x={971} y={536} size={42} fill={paper}>Trained PPO policy</Word>
        <Word x={971} y={587} size={27} fill={warm}>Eligible actions only</Word>
      </g>
      <g opacity={p}>
        <Word x={302} y={592} size={120} weight={800}>{demo.taskCode}</Word>
        <Word x={674} y={578} size={76} fill={orange}>→</Word>
        <Word x={927} y={595} size={156} fill={warm} weight={800}>{demo.robotId}</Word>
      </g>
      <g opacity={lock}>
        <Word x={303} y={758} size={44} weight={750}>Intelligent assignment based on learned policy</Word>
        <Word x={307} y={811} size={29} fill={muted}>Medication delivery · Pharmacy → Ward A</Word>
        <Word x={307} y={861} size={23} fill={muted}>Demo assignment</Word>
      </g>
    </g>
    <defs><clipPath id="v5Inference"><circle cx="673" cy="515" r={mix(15,1490,iris)}/></clipPath></defs>
  </>;
}

export const PPOSchedulingPrototypeV5 = () => {
  const f=useCurrentFrame();
  const dark=f>=240 && f<404;
  const caption=captions.find(({from,to})=>f>=from && f<to);
  return <AbsoluteFill style={{background:paper,fontFamily:"Inter, Arial, Noto Sans CJK TC, sans-serif"}}>
    <svg width={1920} height={1080}>
      {f<75 ? <Intro f={f}/> : f<150 ? <Filter f={f}/> : f<240 ? <State f={f}/> : f<390 ? <Learning f={f}/> : <Decision f={f}/>}
    </svg>
    <div style={{position:"absolute",top:58,left:126,display:"flex",alignItems:"center",gap:10,fontSize:32,fontWeight:750,color:dark ? paper : ink}}>
      <Img src={staticFile("dashboard-v2/brand-mark.svg")} style={{width:45,height:37}} alt=""/><span>Medi<span style={{color:dark ? warm : orange}}>Sync</span></span>
    </div>
    {caption && <div style={{position:"absolute",alignSelf:"center",bottom:45,padding:"9px 24px",borderRadius:8,background:ink,color:paper,fontSize:32}}>{caption.text}</div>}
    <Audio src={staticFile("ppo-v5/voice.wav")}/>
    <Audio src={staticFile("ppo-v5/score.wav")}/>
  </AbsoluteFill>;
};
