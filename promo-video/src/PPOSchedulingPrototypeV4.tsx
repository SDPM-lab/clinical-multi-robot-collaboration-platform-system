import {AbsoluteFill, Audio, Easing, Img, interpolate, staticFile, useCurrentFrame} from "remotion";
import fleet from "./ppo-scheduling-demo.json";
import captions from "./ppo-v4-captions.json";

const paper = "#fbf8f3";
const ink = "#201a17";
const orange = "#e95019";
const warm = "#ff8656";
const slate = "#73665e";
const ease = (frame: number, start: number, end: number) =>
  interpolate(frame, [start, end], [0, 1], {extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.bezier(.3, 0, .22, 1)});
const lerp = (from: number, to: number, p: number) => from + (to - from) * p;

const nodeSlots = [
  [434, 420, 61], [445, 673, 68], [758, 776, 76], [1154, 776, 76],
  [1451, 650, 67], [1490, 403, 57], [960, 276, 54],
];
const anchors = [
  {angle: 3.65, title: "State", detail: "Observe", label: [370, 347]},
  {angle: 5.02, title: "Action", detail: "Interact", label: [1248, 331]},
  {angle: 6.57, title: "Reward", detail: "Environment feedback", label: [1535, 684]},
  {angle: 8.4, title: "Policy update", detail: "Learn from experience", label: [488, 785]},
];
const orbit = (a: number, rise: number) => {
  const depth = Math.sin(a);
  const perspective = 1 / (1 - .14 * depth);
  return {x: 960 + 470 * Math.cos(a) * perspective, y: 548 + 167 * depth * perspective - rise, depth};
};
const track = (from: number, to: number, offset = 0) =>
  Array.from({length: 65}, (_, i) => {
    const p = orbit(lerp(from, to, i / 64), offset);
    return `${i ? "L" : "M"}${p.x},${p.y}`;
  }).join(" ");

function Opening({f}: {f: number}) {
  const settle = ease(f, 12, 33);
  const tail = ease(f, 52, 59);
  return <>
    {["P","P","O"].map((letter, i) => {
      const a = ease(f, i * 3 - 4, 23 + i * 3);
      return <text key={i} x={721 + i * 235 + (1 - a) * (i - 1) * 175}
        y={548 + (1 - a) * (i === 1 ? 160 : -100)} textAnchor="middle" fontSize={296 * lerp(.68 + i * .33, 1, a) * lerp(1.07, 1, settle)}
        fill={orange} fontWeight="800" opacity={lerp(.22, 1, a)}>{letter}</text>;
    })}
    <g clipPath="url(#introText)">
      <text x="960" y={646 + 33 * (1 - settle)} textAnchor="middle" fontSize="64" fontWeight="700">Proximal Policy Optimization</text>
      <text x="960" y={714 + 29 * (1 - settle)} textAnchor="middle" fontSize="32" fill={slate}>Reinforcement Learning for Intelligent Scheduling</text>
    </g>
    <defs><clipPath id="introText"><rect x="310" y="565" width={1300 * settle} height="172" /></clipPath></defs>
    {nodeSlots.map(([x, y], i) => <circle key={i} cx={lerp(960, x, ease(f, 44, 59))} cy={lerp(475, y, ease(f, 44, 59))} r={lerp(0, 6, tail)} fill={orange} opacity={.42 * tail}/>)}
  </>;
}

function Candidates({f}: {f: number}) {
  const matched = ease(f, 99, 123);
  return <>
    <text x="126" y="204" fontSize="76" fontWeight="700">Capability matching</text>
    <text x="126" y="251" fontSize="29" fill={slate}>Screen for capability and availability</text>
    <circle cx="960" cy="522" r={lerp(22, 154, ease(f, 60, 79))} fill={ink}/>
    <g textAnchor="middle" fill={paper} opacity={ease(f, 67, 80)}>
      <text x="960" y="482" fontSize="29" fill={warm} fontWeight="700">{fleet.taskCode} · HIGH</text>
      <text x="960" y="530" fontSize="31" fontWeight="700">Medication delivery</text>
      <text x="960" y="571" fontSize="25">Pharmacy → Ward A</text>
    </g>
    {fleet.robots.map((robot, i) => {
      const [x,y,r] = nodeSlots[i];
      const grow = ease(f, 59 + i % 3, 84 + i % 3);
      const dim = robot.eligible ? 0 : matched * .65;
      const label = robot.eligible ? "Eligible" : robot.capabilityMatch ? "Charging" : "Capability mismatch";
      return <g key={robot.id} transform={`translate(${x} ${y})`} opacity={1 - dim * .54}>
        <ellipse cx="0" cy={r * .78} rx={r * .9 * grow} ry="14" fill={ink} opacity=".075"/>
        <circle r={lerp(6, r, grow)} fill={robot.eligible ? "#fce2d3" : "#ede6df"} stroke={robot.eligible ? orange : "#c9bbb0"} strokeWidth={robot.eligible ? 4 : 2}/>
        <text y="11" textAnchor="middle" fill={robot.eligible ? "#b53b10" : ink} fontSize={r * .51} fontWeight="700" opacity={grow}>{robot.id}</text>
        <text y={r + 31} textAnchor="middle" fontSize="22" fill={slate} opacity={matched}>{label}</text>
      </g>;
    })}
  </>;
}

function StateVector({f}: {f: number}) {
  const assembled = ease(f, 164, 208);
  const reveal = ease(f, 197, 216);
  const converge = ease(f, 232, 239);
  const dots = Array.from({length: 98}, (_, i) => {
    const task = i < 41;
    const system = i === 97;
    const idx = task ? i : i - 41;
    const startX = system ? 1565 : task ? 210 + idx % 9 * 42 : 1050 + idx % 8 * 53;
    const startY = system ? 354 : task ? 474 + Math.floor(idx / 9) * 41 : 481 + Math.floor(idx / 8) * 35;
    const row = Math.floor(i / 14);
    const col = i % 14;
    const z = row / 6;
    const x = lerp(startX, 876 + col * (43 + z * 7) - z * 38, assembled);
    const y = lerp(startY, 363 + row * 62 + col * .8, assembled);
    return {i, x, y, size: lerp(task ? 8 : system ? 23 : 10, 10 + 6 * z, assembled), color: task ? orange : system ? ink : "#847269"};
  });
  return <>
    <g opacity={(1 - assembled) * .95} fontSize="28" fill={slate}>
      <text x="208" y="420">Task features</text><text x="1050" y="420">Fleet features</text><text x="1480" y="300">System load</text>
    </g>
    <g opacity={reveal * (1 - converge)}>
      <text x="126" y="545" fontSize="244" fontWeight="800" fill={orange}>98D</text>
      <text x="141" y="614" fontSize="52" fontWeight="700">State representation</text>
      <text x="143" y="670" fontSize="29" fill={slate}>Task · Fleet · System load</text>
    </g>
    {dots.map(({i,x,y,size,color}) => <circle key={i} cx={lerp(x,960,converge)} cy={lerp(y,548,converge)}
      r={lerp(size,3,converge)} fill={color} opacity={1 - converge * .78}/>)}
  </>;
}

function Learning({f}: {f: number}) {
  const switchProgress = ease(f, 337, 351);
  const start = anchors[0].angle;
  const end = start + 2 * Math.PI;
  const phase = interpolate(f, [249, 272, 292, 319, 332], [0, (anchors[1].angle-start)/(2*Math.PI), (anchors[2].angle-start)/(2*Math.PI), (anchors[3].angle-start)/(2*Math.PI), 1], {extrapolateLeft:"clamp", extrapolateRight:"clamp"});
  const point = orbit(lerp(start, end, phase), 0);
  const core = ease(f, 307, 329);
  return <>
    <rect width="1920" height="1080" fill={ink}/>
    <g opacity={1-switchProgress}>
      <text x="126" y="186" fontSize="30" fontWeight="700" fill={warm} letterSpacing="5">OFFLINE TRAINING</text>
      <text x="126" y="252" fontSize="68" fill={paper} fontWeight="700">Learn from experience</text>
      <path d={track(Math.PI, 2*Math.PI)} fill="none" stroke="#655248" strokeWidth="3"/>
      <path d={track(0, Math.PI,-16)} fill="none" stroke="#594033" strokeWidth="2"/>
      <g transform={`translate(960 548) scale(${lerp(.12,1,ease(f,240,254))})`}>
        <ellipse cy="45" rx="131" ry="83" fill="#573a31"/>
        <ellipse cy={lerp(19,9,core)} rx="132" ry="83" fill="#8a4b35"/>
        <ellipse rx="128" ry="81" fill="#f9855a" stroke="#ffac8c" strokeWidth="2"/>
        <text textAnchor="middle" y="9" fill={ink} fontSize="31" fontWeight="800">PPO Policy</text>
      </g>
      <path d={track(0, Math.PI)} fill="none" stroke="#bb7760" strokeWidth="3"/>
      <path d={track(start, lerp(start,end,phase))} fill="none" stroke={warm} opacity=".57" strokeWidth="5"/>
      {anchors.map(({angle,title,detail,label}, i) => {
        const p = orbit(angle,0);
        const active = ease(f, [248,264,280,301][i], [256,273,289,314][i]);
        return <g key={title}>
          <circle cx={p.x} cy={p.y} r={lerp(11,16,active)} fill={active>.5 ? warm : "#927263"}/>
          <text x={label[0]} y={label[1]} textAnchor="middle" fill={paper} fontSize="34" fontWeight="700">{title}</text>
          <text x={label[0]} y={label[1]+35} textAnchor="middle" fill="#e0b9aa" fontSize="23">{detail}</text>
        </g>;
      })}
      <circle cx={point.x} cy={point.y} r={14 + 3 * point.depth} fill={warm} stroke={paper} strokeWidth="2" opacity={1-ease(f,332,337)}/>
    </g>
    <g clipPath="url(#inference)">
      <rect width="1920" height="1080" fill={paper}/>
      <text x="126" y="186" fontSize="30" fontWeight="700" fill={orange} letterSpacing="5">INFERENCE</text>
      <text x="126" y="264" fontSize="66" fontWeight="700">Use the trained policy</text>
      <circle cx="960" cy="548" r="130" fill={orange}/>
      <text x="960" y="538" fill={paper} textAnchor="middle" fontSize="29" fontWeight="700">Trained</text>
      <text x="960" y="577" fill={paper} textAnchor="middle" fontSize="29" fontWeight="700">PPO Policy</text>
      <text x="461" y="554" textAnchor="middle" fill={slate} fontSize="39">Current state →</text>
      <text x="1454" y="554" textAnchor="middle" fill={slate} fontSize="39">→ Scheduling decision</text>
    </g>
    <defs><clipPath id="inference"><circle cx="960" cy="548" r={switchProgress*1140}/></clipPath></defs>
  </>;
}

function Assignment({f}: {f: number}) {
  const focus = ease(f, 369, 394);
  const lock = ease(f, 392, 410);
  return <>
    <text x="126" y="247" fontSize="76" fontWeight="700">Intelligent assignment</text>
    <circle cx={lerp(960,1170,focus)} cy="548" r={lerp(130,147,focus)} fill={orange}/>
    <text x={lerp(960,1170,focus)} y="573" textAnchor="middle" fill={paper} fontSize="78" fontWeight="800">{fleet.robotId}</text>
    <g opacity={lerp(.83,.32,focus)}>
      <circle cx="1514" cy="548" r="79" fill="#eae0d9" stroke="#99867a" strokeWidth="2"/>
      <text x="1514" y="564" textAnchor="middle" fill={ink} fontSize="47" fontWeight="700">M02</text>
    </g>
    <g opacity={focus}>
      <text x="666" y="576" textAnchor="middle" fontSize="96" fontWeight="800">{fleet.taskCode}</text>
      <text x="904" y="569" textAnchor="middle" fontSize="59" fill={orange}>→</text>
    </g>
    <g opacity={lock}>
      <text x="960" y="798" textAnchor="middle" fontSize="43" fontWeight="700">Task assigned</text>
      <text x="960" y="848" textAnchor="middle" fontSize="29" fill={slate}>Medication delivery · Pharmacy → Ward A</text>
    </g>
  </>;
}

export const PPOSchedulingPrototypeV4 = () => {
  const f = useCurrentFrame();
  const caption = captions.find(({from,to}) => f >= from && f < to);
  return <AbsoluteFill style={{background:paper,fontFamily:"Inter, Arial, sans-serif", color:ink}}>
    <svg width="1920" height="1080" fill={ink}>
      {f < 60 ? <Opening f={f}/> : f < 150 ? <Candidates f={f}/> : f < 240 ? <StateVector f={f}/> : f < 360 ? <Learning f={f}/> : <Assignment f={f}/>}
    </svg>
    <div style={{position:"absolute",top:65,left:126,display:"flex",alignItems:"center",gap:10,fontSize:32,fontWeight:750,color:f>=240&&f<350?paper:ink}}>
      <Img src={staticFile("dashboard-v2/brand-mark.svg")} style={{width:45,height:38}} alt=""/>
      <span>Medi<span style={{color:f>=240&&f<350?warm:orange}}>Sync</span></span>
    </div>
    {caption && <div style={{position:"absolute",bottom:47,alignSelf:"center",background:ink,color:paper,borderRadius:8,padding:"8px 22px",fontSize:32,fontFamily:"Noto Sans CJK TC, sans-serif"}}>{caption.text}</div>}
    <Audio src={staticFile("ppo-v4/voice.wav")}/>
    <Audio src={staticFile("ppo-v4/score.wav")}/>
  </AbsoluteFill>;
};
