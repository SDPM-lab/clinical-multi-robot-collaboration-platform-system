import type { CSSProperties } from "react";
import { AbsoluteFill, Audio, Easing, Img, Sequence, interpolate, staticFile, useCurrentFrame } from "remotion";
import route from "./schedule-history-v1-route.json";
import "./schedule-history-v1.css";
import "./schedule-history-v3.css";
import "./schedule-history-v4.css";
import "./schedule-history-v6.css";

const asset = (file: string) => staticFile(`schedule-history-phase-v3/${file}`);
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
  {id:"MS-0237",type:"Supply Delivery",robot:"W03",from:"Pantry",to:"Ward B",priority:"Low",status:"Completed",created:"07:25",scheduled:"07:34",start:"07:37",finish:"07:45",capability:"General delivery",accent:"#e0f2eb"},
  {id:"MS-0234",type:"Medication Delivery",robot:"M01",from:"Pharmacy",to:"Nurse Station",priority:"High",status:"Completed",created:"07:06",scheduled:"07:15",start:"07:15",finish:"07:24",capability:"Medicine delivery",accent:"#ffe9d4"},
  {id:"MS-0230",type:"Waste Collection",robot:"C02",from:"Ward A",to:"Waste Return",priority:"Normal",status:"Completed",created:"06:46",scheduled:"06:50",start:"06:52",finish:"07:03",capability:"General delivery",accent:"#f9e5e0"},
];
const selected = tasks[0];
const minute = (time: string) => Number(time.slice(0,2))*60+Number(time.slice(3));
const delay = (task: Task) => task.start ? Math.max(0,minute(task.start)-minute(task.scheduled)) : null;

const metrics = [
  {label:"Total Tasks",key:"Total",value:tasks.length,mark:"≡"},
  {label:"Completed",key:"Completed",value:tasks.filter(t=>t.status==="Completed").length,mark:"✓"},
  {label:"Cancelled",key:"Cancelled",value:tasks.filter(t=>t.status==="Cancelled").length,mark:"−"},
  {label:"Failed",key:"Failed",value:tasks.filter(t=>t.status==="Failed").length,mark:"!"},
] as const;
const timeline = [
  {label:"Task Created",time:selected.created,note:"",completed:true},
  ...(selected.start ? [{label:"Execution Started",time:selected.start,note:selected.from,completed:true}] : []),
  {label:`Task ${selected.status}`,time:selected.finish,note:selected.status==="Completed"?selected.to:"",completed:selected.status==="Completed"},
];
const captions = [
  [24,65,"不只即時掌握任務，"],
  [65,121,"更能回顧每一次執行成果。"],
  [139,192,"從整體統計到歷史紀錄，"],
  [192,240,"每筆任務都清楚呈現。"],
  [258,335,"選取紀錄，即可查看任務詳情、"],
  [335,388,"路線資訊與完整執行歷程。"],
] as const;
const rowStart = [117,126,135,144,152,160,168,176];

function Stats({f,opening}:{f:number;opening:number}) {
  const glide = step(f,4,91);
  return <div className="sh3-metric-plane" style={{
    transform:`perspective(2300px) translateX(${13*(1-glide)}px) rotateY(${5*(1-glide)}deg) rotateX(${4*(1-glide)}deg)`,
  }}>
    {metrics.map(({label,key,value},i)=>{
      const cue=23+i*10;
      const land=step(f,cue,cue+24);
      const lift=step(f,cue+24,cue+31)*(1-step(f,cue+32,cue+44));
      const sheen=step(f,cue+23,cue+39);
      const count=Math.round(value*step(f,cue+23,cue+40));
      return <div className="sh3-metric-slot" key={key} style={{height:blend(104,148,opening)}}>
        <i className="sh3-contact" style={{opacity:.19*lift,transform:`translate(${4*lift}px,${15*lift}px) scale(${1+.044*lift})`}}/>
        <section className={`sh3-metric ${key==="Total"?"sh3-metric-active":""}`} style={{
          opacity:step(f,cue,cue+8),padding:`${blend(11,19,opening)}px ${blend(17,22,opening)}px`,
          transform:`translate3d(${-14*(1-land)}px,${53*(1-land)-9*lift}px,${-58*(1-land)+16*lift}px) rotateY(${-16*(1-land)}deg) rotateX(${9*(1-land)}deg)`,
        }}>
          <div className="sh3-metric-top"><span>{label}</span><MetricIcon index={i} color={colors[key]}/></div>
          <div className="sh3-reading"><strong style={{fontSize:blend(42,58,opening)}}>{count}</strong><small>↑ +{count} vs previous day</small></div>
          {f>=cue+23&&f<cue+39&&<i className="sh3-sheen" style={{left:`${-28+150*sheen}%`,opacity:.36*Math.sin(Math.PI*sheen)}}/>}
        </section>
      </div>;
    })}
  </div>;
}

function MetricIcon({index,color}:{index:number;color:string}) {
  const paths=["M5 6h14M5 12h14M5 18h14","M8 12l3 3 5-6","M7 17 17 7","M12 8v5m0 3h.01"];
  return <svg className="sh3-metric-icon" style={{color,background:`${color}18`}}
    viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" aria-hidden>
    {index===1||index===2?<circle cx="12" cy="12" r="9"/>:null}
    {index===3?<path d="m12 3 10 17H2Z" strokeLinejoin="round"/>:null}
    <path d={paths[index]}/>
  </svg>;
}

function Route({f}:{f:number}) {
  return <>
    <div className="sh-panel-title">Task Route <small>· {selected.id}</small><span>1F</span></div>
    <div className="sh-map">
      <svg viewBox={route.viewBox} aria-label="Hospital navigation reference route">
        <path d={route.lanes} fill="none" stroke="#d9ded9" strokeWidth=".16"/>
        <path d={route.path} fill="none" stroke="#e58d60" strokeWidth=".29" strokeLinejoin="round"
          strokeLinecap="round" pathLength="1" strokeDasharray="1" strokeDashoffset={1-step(f,325,341)}/>
        {route.points.map((p,i)=><circle key={p.x} cx={p.x} cy={p.y} r=".53" fill={i?"#dc855b":"#fff"} stroke={i?"white":"#dc855b"} strokeWidth=".22"/>)}
      </svg>
      <div className="sh-route-labels"><span><i/>{selected.from}</span><span><i/>{selected.to}</span></div>
    </div>
    <p className="sh-route-hint">Source and destination reference only. This map does not show the recorded execution path.</p>
  </>;
}

export const ScheduleHistoryPhaseV6 = () => {
  const f = useCurrentFrame();
  const detail = step(f,291,316);
  const routeIn = step(f,315,335);
  const overview = step(f,366,389);
  const assembly = step(f,96,108);
  const reflow = step(f,240,290);
  const workspaceLeft = blend(80,28,reflow);
  const workspaceWidth = blend(1760,1310,reflow);
  const title = step(f,5,25)*(1-step(f,82,96));
  const hovered = f>=217;
  const clicked = f>=225;
  const caption = captions.find(([start,end])=>f>=start&&f<end);
  const cursor = step(f,196,222);
  const badge = step(f,225,240);
  const journey = step(f,339,365);

  return <AbsoluteFill className="sh-film sh-v3 sh-v4 sh-v6">
      {f<105&&<Img className="sh4-stage-brand" src={staticFile("schedule-history-phase-v6/medisync-wordmark.png")}
        style={{opacity:1-step(f,95,105)}} alt="MediSync"/>}
      {f>=366&&      <header className="sh-nav" aria-label="MediSync navigation" style={{opacity:overview}}>
        <Img className="sh3-brand" src={asset("nav-brand.png")} alt="MediSync"/>
        <nav><span>Dashboard</span><span>Task Dispatch</span><strong>Schedule History</strong><span>Live Map</span><span>Robot Status</span></nav>
        <Img className="sh3-nav-controls" src={asset("nav-controls.png")} alt="Notifications, connection, theme, fullscreen and user"/>
      </header>}
    <div className="sh-world" style={{transformOrigin:"50% 50%",transform:`scale(${1+.018*step(f,313,350)*(1-overview)})`}}>
      <div className="sh-stats-space" style={{
        left:workspaceLeft,width:workspaceWidth,top:blend(546,94,assembly),
      }}><Stats f={f} opening={1-assembly}/></div>

      <section className="sh-records sh-panel" style={{
        left:workspaceLeft,width:workspaceWidth,opacity:step(f,108,117),
        transform:`translateY(${18*(1-step(f,107,117))}px)`,
      }}>
        <header className="sh-toolbar">
          <span className="sh-search"><svg viewBox="0 0 20 20" width="17" height="17"><circle cx="8" cy="8" r="5" fill="none" stroke="currentColor" strokeWidth="1.5"/><path d="m12 12 4 4" stroke="currentColor" strokeWidth="1.5"/></svg> Search tasks</span>
          <span className="sh3-control" aria-label="Filter"><svg viewBox="0 0 20 20" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="1.6"><path d="M3 4h14l-5 6v5l-4 2v-7Z"/></svg></span>
          <span className="sh3-date-controls"><span aria-label="Previous">‹</span><span className="sh-date" aria-label="Date picker"><svg viewBox="0 0 20 20" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.5"><rect x="3" y="5" width="14" height="12" rx="2"/><path d="M3 9h14M7 3v4m6-4v4"/></svg> {day}</span><span aria-label="Next">›</span></span>
          <span className="sh3-control" aria-label="Refresh">↻</span>
          <span className="sh-modes"><b>Daily</b><span>Weekly</span><span>Monthly</span></span>
        </header>
        <div className="sh3-range">Fri, November 27, 2026 – Fri, November 27, 2026</div>
        <div className="sh-column-head sh-grid">{["Task Type","Actual Time","Start Delay","Robot","Source → Destination","Priority","Status","Duration"].map(h=><span key={h}>{h}</span>)}</div>
        <p className="sh-day">Fri, November 27, 2026 <small>{tasks.length} tasks</small></p>
        {tasks.map((t,i)=>{
          const cue=rowStart[i], land=cue+18, p=step(f,cue,land);
          return <div key={t.id} className={`sh-row sh-grid ${i===0&&(clicked?"sh-row-active":hovered?"sh3-hover":"")}`}
            style={{opacity:step(f,cue,cue+5),boxShadow:`0 ${5*(1-p)}px ${12*(1-p)}px rgba(48,42,34,${.075*(1-p)})`,
              transform:`perspective(1500px) translate3d(${-15*(1-p)}px,${-8*(1-p)}px,${22*(1-p)}px) rotateX(${5*(1-p)}deg)`}}>
            <span className="sh-task"><strong>{t.type}</strong><small>{t.id}</small></span>
            <span className="sh-time">{t.start?`${t.start}–${t.finish}`:"—"}</span>
            <span className={(delay(t)??0)>0?"sh3-delay":undefined}>{delay(t)===null?"—":`${delay(t)} min`}</span><span>{t.robot}</span>
            <span className="sh-endpoints">{t.from} <i>→</i> {t.to}</span>
            <span className={`sh-priority sh-${t.priority.toLowerCase()}`}>{t.priority}</span>
            <span className="sh-state" style={{"--sh3-status":colors[t.status]} as CSSProperties}><i/>{t.status}</span>
            <span>{t.start?`${minute(t.finish)-minute(t.start)} min`:"—"}</span>
            <i className="sh-seam" style={{opacity:step(f,land-2,land)*(1-step(f,land+1,land+7))}}/>
          </div>;
        })}
      </section>

      {f>=291&&<aside className="sh-details">
        <section className="sh-panel sh-facts" style={{clipPath:`inset(0 0 0 ${100*(1-detail)}% round 14px)`}}>
          <div className="sh-panel-title">Task Details <small>· {selected.id}</small></div>
          <dl>{[["Robot",selected.robot],["Note","Unavailable"],
            ["Required Capabilities",selected.capability],["Created At",`${day} ${selected.created}`],
            ["Scheduled Start",`${day} ${selected.scheduled}`]].map(([label,value],i)=>
            <div key={label} style={{opacity:step(f,299+i*3,307+i*3)}}><dt>{label}</dt><dd>{label==="Required Capabilities"?<span>{value}</span>:value}</dd></div>)}</dl>
        </section>
        <section className="sh-panel sh-route-timeline" style={{opacity:routeIn,transform:`translateY(${12*(1-routeIn)}px)`}}>
          <Route f={f}/>
          <div className="sh-timeline">
            <h3>Task Timeline</h3>
            <div className="sh-timeline-track"><i style={{height:`${100*journey}%`}}/></div>
            <ol>{timeline.map((item,i)=>{
              const on=step(f,338+i*10,345+i*10);
              return <li key={item.label} style={{opacity:on}}>
                <span className="sh-node">{item.completed?"✓":"!"}</span>
                <div><strong>{item.label}</strong>{item.note&&<small>{item.note}</small>}</div>
                <time>{item.time}</time>
              </li>;
            })}</ol>
          </div>
        </section>
      </aside>}

      {f>=196&&f<244&&<svg width="34" height="40" viewBox="0 0 34 40" className="sh-pointer"
        style={{left:blend(615,325,cursor),top:blend(555,435,cursor),opacity:step(f,196,202)*(1-step(f,231,244))}}>
        {clicked&&<circle cx="5" cy="4" r={4+14*badge} fill="none" stroke="#eb8650" strokeWidth="2" opacity={1-badge}/>}
        <path d="M4 3v27l7-7 4 10 5-2-5-10h9Z" fill="#fff" stroke="#2d2d2c" strokeWidth="1.7"/>
      </svg>}
    </div>
    {f<96&&<div className="sh3-title sh4-title" style={{opacity:title}}>
      <strong style={{clipPath:`inset(0 ${(1-step(f,7,24))*100}% 0 0)`}}>EVERY TASK. EVERY DETAIL.</strong>
      <span className="sh6-support" style={{opacity:step(f,14,25)}}>A complete record of every operation.</span>
      <span className="sh6-secondary" style={{opacity:step(f,20,33),letterSpacing:blend(.5,0,step(f,20,44))}}>Review task outcomes, execution history, and operational details — all in one place.</span>
    </div>}
    {caption&&<div className="sh-caption" lang="zh-Hant">{caption[2]}</div>}
    <Sequence from={21} layout="none"><Audio src={staticFile("schedule-history-phase-v4/voice.mp3")}/></Sequence>
    <Audio src={staticFile("schedule-history-phase-v6/sound.wav")} volume={.75}/>
  </AbsoluteFill>;
};
