import { AbsoluteFill, Audio, Easing, Img, Sequence, interpolate, staticFile, useCurrentFrame } from "remotion";
import route from "./schedule-history-v1-route.json";
import "./schedule-history-v1.css";

const asset = (file: string) => staticFile(`schedule-history-phase-v1/${file}`);
const ease = Easing.bezier(.33, 0, .23, 1);
const step = (f: number, a: number, b: number) => interpolate(f, [a,b], [0,1], {
  easing: ease, extrapolateLeft: "clamp", extrapolateRight: "clamp",
});
const blend = (a: number, b: number, t: number) => a + (b-a)*t;
const day = "2026/11/27";
const colors = {Total: "#ff965f", Completed: "#679a7b", Cancelled: "#6489c7", Failed: "#c47c70"};
type Status = Exclude<keyof typeof colors, "Total">;
type Task = {id: string; type: string; robot: string; from: string; to: string; priority: string; status: Status; created: string; scheduled: string; start?: string; finish: string; capability: string; accent: string};
const tasks: Task[] = [
  {id:"MS-0248",type:"Medication Delivery",robot:"M01",from:"Pharmacy",to:"Ward A",priority:"High",status:"Completed",created:"09:02",scheduled:"09:10",start:"09:10",finish:"09:22",capability:"Medicine delivery",accent:"#ffe9d4"},
  {id:"MS-0245",type:"Specimen Transport",robot:"M02",from:"Ward B",to:"Laboratory",priority:"Urgent",status:"Completed",created:"08:46",scheduled:"08:50",start:"08:51",finish:"09:00",capability:"Delivery",accent:"#f0e4f7"},
  {id:"MS-0243",type:"Waste Collection",robot:"C01",from:"Ward B",to:"Waste Return",priority:"Normal",status:"Failed",created:"08:28",scheduled:"08:35",start:"08:35",finish:"08:40",capability:"Delivery",accent:"#f9e5e0"},
  {id:"MS-0241",type:"Supply Delivery",robot:"W01",from:"Pantry",to:"Ward A",priority:"Low",status:"Cancelled",created:"08:10",scheduled:"08:25",finish:"08:18",capability:"Delivery",accent:"#e0f2eb"},
  {id:"MS-0239",type:"Document Delivery",robot:"W02",from:"Nurse Station",to:"Ward B",priority:"Normal",status:"Completed",created:"07:48",scheduled:"08:00",start:"08:00",finish:"08:08",capability:"Delivery",accent:"#e6f0fb"},
];
const selected = tasks[0];
const metrics = [
  {label:"Total Tasks",key:"Total",value:tasks.length,mark:"≡"},
  {label:"Completed",key:"Completed",value:tasks.filter(t=>t.status==="Completed").length,mark:"✓"},
  {label:"Cancelled",key:"Cancelled",value:tasks.filter(t=>t.status==="Cancelled").length,mark:"−"},
  {label:"Failed",key:"Failed",value:tasks.filter(t=>t.status==="Failed").length,mark:"!"},
] as const;
const minute = (time: string) => Number(time.slice(0,2))*60+Number(time.slice(3));
const timeline = [{label:"Task Created",time:selected.created,note:""},{
  label:"Execution Started",time:selected.start!,note:selected.from,
},{label:"Task Completed",time:selected.finish,note:selected.to}];
const captions = [
  [9,119,"每一次任務，都是可追溯的紀錄。"],
  [119,239,"從完成情況、任務明細，到執行歷程，"],
  [239,320,"MediSync 讓每個環節都清楚可查。"],
] as const;
const trend = (key: (typeof metrics)[number]["key"]) => {
  const ordered = [...tasks].sort((a,b) => minute(a.finish)-minute(b.finish));
  let count = 0;
  const points = ordered.map((task,i) => {
    if (key==="Total" || key===task.status) count++;
    return `H${24 + i*23} V${27 - 4*count}`;
  });
  return `M1 27 ${points.join(" ")} H119`;
};
const rowStart = [100,109,118,127,136];

function Stats({f}:{f:number}) {
  return <div className="sh-stats">{metrics.map(({label,key,value,mark},i)=>
    <section key={key} style={{borderLeftColor:colors[key]}}>
      <div><span>{label}</span><span className="sh-stat-mark" style={{color:colors[key]}} aria-hidden>{mark}</span></div>
      <strong>{Math.round(value*step(f,31+i*4,51+i*4))}</strong>
      <svg className="sh-stat-line" viewBox="0 0 120 30" aria-hidden>
        <path d={trend(key)} fill="none" stroke={colors[key]} strokeWidth="2"/>
      </svg>
    </section>)}</div>;
}

function Route({f}:{f:number}) {
  return <>
    <div className="sh-panel-title">Task Route <small>· {selected.id}</small><span>1F</span></div>
    <div className="sh-map">
      <svg viewBox={route.viewBox} aria-label="Hospital navigation reference route">
        <path d={route.lanes} fill="none" stroke="#d9ded9" strokeWidth=".16"/>
        <path d={route.path} fill="none" stroke="#da743f" strokeWidth=".29" strokeLinejoin="round"
          strokeLinecap="round" pathLength="1" strokeDasharray="1" strokeDashoffset={1-step(f,203,233)}/>
        {route.points.map((p,i)=><circle key={p.x} cx={p.x} cy={p.y} r=".53" fill={i?"#679a7b":"#ff965f"} stroke="white" strokeWidth=".22"/>)}
      </svg>
      <div className="sh-route-labels"><span><i/>{selected.from}</span><span><i/>{selected.to}</span></div>
    </div>
    <p className="sh-route-hint">Source and destination reference only. This map does not show the recorded execution path.</p>
  </>;
}

export const ScheduleHistoryPhaseV1 = () => {
  const f = useCurrentFrame();
  const handoff = step(f,9,33);
  const settle = step(f,28,64);
  const detail = step(f,170,200);
  const lift = step(f,300,330);
  const timelineFocus = step(f,239,258)*(1-lift);
  const introTitle = step(f,60,68);
  const titleLand = step(f,80,100);
  const hovered = f>=163;
  const clicked = f>=174;
  const caption = captions.find(([start,end])=>f>=start&&f<end);
  const zoom = 1 + .09*timelineFocus;
  const tableWidth = blend(1772,1190,detail);
  const cursor = step(f,151,173);
  const badge = step(f,174,190);
  const journey = step(f,244,287);

  return <AbsoluteFill className="sh-film">
    <div className="sh-world" style={{transformOrigin:"95% 79%",
      transform:`translate(${-24*timelineFocus}px,${-10*timelineFocus}px) scale(${zoom})`}}>
      <header className="sh-nav">
        <div><Img src={staticFile("dashboard-v2/brand-mark.svg")}/><b>Medi<em>Sync</em></b></div>
        <nav><span>Dashboard</span><span>Task Dispatch</span><strong>Schedule History</strong><span>Live Map</span><span>Robot Status</span></nav>
        <span className="sh-user">M</span>
      </header>
      <div className="sh-stats-space" style={{
        width:tableWidth,opacity:step(f,17,36),transform:`perspective(2100px) translateX(${46*(1-settle)}px) rotateY(${-12*(1-settle)}deg) rotateX(${7*(1-settle)}deg)`,
      }}><Stats f={f}/></div>

      <div className="sh-product-title" style={{opacity:introTitle,left:blend(72,74,titleLand),top:blend(257,222,titleLand)}}>
        <strong style={{fontSize:blend(75,27,titleLand),letterSpacing:blend(-2.7,-.45,titleLand)}}>EVERY TASK. ACCOUNTED FOR.</strong>
        <span style={{fontSize:blend(24,17,titleLand),opacity:1-.24*titleLand}}>A complete record of every operation.</span>
      </div>

      <section className="sh-records sh-panel" style={{width:tableWidth,opacity:step(f,87,101),transform:`translateY(${14*(1-step(f,87,105))}px)`}}>
        <header className="sh-toolbar">
          <span className="sh-search"><svg viewBox="0 0 20 20" width="17" height="17"><circle cx="8" cy="8" r="5" fill="none" stroke="currentColor" strokeWidth="1.5"/><path d="m12 12 4 4" stroke="currentColor" strokeWidth="1.5"/></svg> Search tasks</span>
          <span className="sh-date">‹ &nbsp; {day} &nbsp; ›</span>
          <span className="sh-modes"><b>Daily</b><span>Weekly</span><span>Monthly</span></span>
        </header>
        <div className="sh-column-head sh-grid">{["Task","Actual Time","Robot","Source → Destination","Priority","Status","Duration"].map(h=><span key={h}>{h}</span>)}</div>
        <p className="sh-day">Fri, November 27, 2026 <small>{tasks.length} tasks</small></p>
        {tasks.map((t,i)=>{
          const cue=rowStart[i], land=cue+15, p=step(f,cue,land);
          return <div key={t.id} className={`sh-row sh-grid ${i===0&&hovered?"sh-row-active":""}`}
            style={{opacity:step(f,cue,cue+5),borderLeftColor:clicked&&i===0?"#ed8651":t.accent,
              transform:`perspective(1500px) translate3d(${-22*(1-p)}px,${-12*(1-p)}px,${30*(1-p)}px) rotateX(${8*(1-p)}deg)`}}>
            <span className="sh-task"><strong>{t.type}</strong><small>{t.id}</small></span>
            <span className="sh-time">{t.start?`${t.start}–${t.finish}`:"—"}</span>
            <span>{t.robot}</span>
            <span className="sh-endpoints">{t.from} <i>→</i> {t.to}</span>
            <span className={`sh-priority sh-${t.priority.toLowerCase()}`}>{t.priority}</span>
            <span className="sh-state" style={{color:colors[t.status]}}><i/>{t.status}</span>
            <span>{t.start?`${minute(t.finish)-minute(t.start)} min`:"—"}</span>
            <i className="sh-seam" style={{opacity:step(f,land-2,land)*(1-step(f,land+1,land+7))}}/>
          </div>;
        })}
      </section>

      <aside className="sh-details" style={{opacity:detail,transform:`translateX(${28*(1-detail)}px)`}}>
        <section className="sh-panel sh-facts">
          <div className="sh-panel-title">Task Details <small>· {selected.id}</small></div>
          <dl>{[["Robot ID",selected.robot],["Task Type",selected.type],["Priority",selected.priority],
            ["Required Capabilities",selected.capability],["Created At",`${day} ${selected.created}`],
            ["Scheduled Start",`${day} ${selected.scheduled}`]].map(([label,value])=>
            <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
        </section>
        <section className="sh-panel sh-route-timeline">
          <Route f={f}/>
          <div className="sh-timeline">
            <h3>Task Timeline</h3>
            <div className="sh-timeline-track"><i style={{height:`${100*journey}%`}}/></div>
            <ol>{timeline.map((item,i)=>{
              const on=step(f,244+i*17,251+i*17);
              return <li key={item.label} style={{opacity:on}}>
                <span className="sh-node">✓</span>
                <div><strong>{item.label}</strong>{item.note&&<small>{item.note}</small>}</div>
                <time>{item.time}</time>
              </li>;
            })}</ol>
          </div>
        </section>
      </aside>

      {f>=150&&f<193&&<svg width="34" height="40" viewBox="0 0 34 40" className="sh-pointer"
        style={{left:blend(750,273,cursor),top:blend(547,476,cursor),opacity:step(f,150,156)*(1-step(f,181,193))}}>
        {clicked&&<circle cx="5" cy="4" r={4+14*badge} fill="none" stroke="#eb8650" strokeWidth="2" opacity={1-badge}/>}
        <path d="M4 3v27l7-7 4 10 5-2-5-10h9Z" fill="#fff" stroke="#2d2d2c" strokeWidth="1.7"/>
      </svg>}
      {f>=175&&f<197&&<span className="sh-travel-id" style={{
        left:blend(97,1413,badge),top:blend(491,153,badge)-33*Math.sin(Math.PI*badge),
        opacity:step(f,175,178)*(1-step(f,185,196)),
      }}>{selected.id}</span>}
    </div>
    {f<33&&<Img className="sh-handoff" src={asset("phase5-handoff.png")}
      style={{opacity:1-handoff,transformOrigin:"86% 65%",transform:`translateX(${-87*handoff}px) scale(${1+.105*handoff})`}}/>}
    {caption&&<div className="sh-caption" lang="zh-Hant">{caption[2]}</div>}
    <Sequence from={6} layout="none"><Audio src={asset("voice.mp3")}/></Sequence>
    <Audio src={asset("sound.wav")} volume={.75}/>
  </AbsoluteFill>;
};
