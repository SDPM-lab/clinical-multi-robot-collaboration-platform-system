import {useEffect, useLayoutEffect, useRef} from "react";
import type {CSSProperties, ReactNode} from "react";
import {
  AbsoluteFill, Audio, Easing, Img, Sequence, interpolate, staticFile,
  useCurrentFrame, useDelayRender,
} from "remotion";
import {createRobotStatusScene} from "./robotStatusScene";
import "../../frontend/src/styles/robotHmi.css";
import "./robot-status-v14.css";

const nativePage = staticFile("robot-status-phase-v9/native-page.png");
const mapPlate = staticFile("live-map-tracking-v2/overhead-handoff.jpg");
const avatar = staticFile("robot-status-phase-v12/agibot-g1.png");
const robots = [
  {id: "C01", status: "Busy", location: "Ward B", battery: 77, temperature: 34, color: "#ff9661"},
  {id: "C02", status: "Idle", location: "Waiting B", battery: 69, temperature: 32, color: "#e8bc25"},
  {id: "M01", status: "Idle", location: "Ward A", battery: 82, temperature: 36, color: "#79766d"},
  {id: "M02", status: "Busy", location: "Laboratory", battery: 91, temperature: 37, color: "#ff9661"},
  {id: "W01", status: "Charging", location: "Charging Station A", battery: 58, temperature: 31, color: "#e8bc25"},
  {id: "W02", status: "Charging", location: "Charging Station A", battery: 48, temperature: 31, color: "#79766d"},
  {id: "W03", status: "Charging", location: "Charging Station B", battery: 65, temperature: 31, color: "#ff9661"},
] as const;
type Robot = (typeof robots)[number];

const initial = robots[1];
const selected = robots[2];
const selectFrame = 180;
const modelName = "Agibot Genie G1";
const settle = Easing.bezier(.35, 0, .25, 1);
const step = (frame: number, start: number, end: number, easing = settle) =>
  interpolate(frame, [start, end], [0, 1], {
    easing, extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

function Icon({children, size = 18}: {children: ReactNode; size?: number}) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
    strokeWidth="1.65" strokeLinecap="round" strokeLinejoin="round" aria-hidden>{children}</svg>;
}

function Fleet({frame, robot}: {frame: number; robot: Robot}) {
  const scroll = step(frame, 73, 129) - step(frame, 140, 161) * .66;
  const pointer = step(frame, 160, 179);
  const click = step(frame, 180, 190);

  return <aside className="robot-control-panel robot-left-hmi" aria-label="Robot Fleet List" style={{position: "relative"}}>
    <label className="robot-search">
      <Icon size={15}><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4 4"/></Icon>
      <input type="search" readOnly aria-label="Search robots" placeholder="Search robots"/>
    </label>
    <div className="robot-floor-filter" role="group" aria-label="Floor filter">
      <button className="is-active" aria-pressed="true">All <span>7</span></button>
      <button aria-pressed="false">1F <span>7</span></button>
    </div>
    <div className="robot-picker" role="listbox" aria-label="Robot Fleet List">
      <div className="v14-fleet-rows" style={{"--fleet-scroll": scroll} as CSSProperties}>
        {robots.map(entry => <div className="robot-list-entry" key={entry.id} role="presentation">
          <button type="button" role="option"
            aria-selected={entry.id === robot.id}
            className={entry.id === robot.id ? "robot-list-item is-active" : "robot-list-item"}
            style={{"--battery-color": entry.color} as CSSProperties}>
            <Img className="robot-list-item__avatar" src={avatar} alt=""/>
            <span className="robot-picker__identity">
              <strong>{entry.id}</strong><small>{entry.status} · F1</small><small>{entry.location}</small>
            </span>
            <span className="robot-list-item__battery"><strong>{entry.battery}%</strong>
              <i><span style={{width: `${entry.battery}%`}}/></i>
            </span>
          </button>
          {entry.id === selected.id && <div className="v14-cursor" aria-hidden
            style={{left: `${93 - 30 * pointer}%`, top: `${98 - 45 * pointer}%`,
              opacity: step(frame, 160, 167) * (1 - step(frame, 185, 196))}}>
            <svg width="30" height="34" viewBox="0 0 30 34">
              {frame >= selectFrame && <circle cx="4" cy="4" r={4 + 12 * click}
                fill="none" stroke="#ff9661" strokeWidth="1.5" opacity={1 - click}/>}
              <path d="M3 2v24l6-6 4 9 4-2-4-9h8Z" fill="#fcfcfc" stroke="#333" strokeWidth="1.5"/>
            </svg>
          </div>}
        </div>)}
      </div>
    </div>
  </aside>;
}

function RobotViewport({angle}: {angle: number}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const scene = useRef<Awaited<ReturnType<typeof createRobotStatusScene>> | null>(null);
  const currentAngle = useRef(angle);
  const {delayRender, continueRender, cancelRender} = useDelayRender();
  useLayoutEffect(() => {
    currentAngle.current = angle;
    scene.current?.drawOrbit(angle);
  }, [angle]);
  useEffect(() => {
    const handle = delayRender("Load original Agibot Genie G1 GLB");
    let active = true;
    createRobotStatusScene(canvas.current!, staticFile("ppo-spatial/AGIBOT_A2D.glb"), 1, 1, false, true)
      .then(renderer => {
        if (!active) { renderer.dispose(); return; }
        scene.current = renderer;
        renderer.drawOrbit(currentAngle.current);
        continueRender(handle);
      })
      .catch(error => { if (active) cancelRender(error); });
    return () => {
      active = false;
      scene.current?.dispose();
      scene.current = null;
      continueRender(handle);
    };
  }, [cancelRender, continueRender, delayRender]);
  return <div className="robot-viewport" aria-label="Agibot Genie G1 3D model">
    <canvas ref={canvas}/>
    <span className="v14-reset-view"><Icon><path d="M3 4v6h6M3 10a8 8 0 1 1 1 7"/></Icon></span>
  </div>;
}

function Inspector({robot, frame}: {robot: Robot; frame: number}) {
  const progress = step(frame, selectFrame, selectFrame + 27, Easing.out(Easing.cubic));
  const battery = interpolate(progress, [0, 1], [initial.battery, selected.battery]);
  const temperature = interpolate(progress, [0, 1], [initial.temperature, selected.temperature]);
  const angle = (135 + temperature * 2.7) * Math.PI / 180;
  const facts: [string, ReactNode][] = [
    ["Robot ID", robot.id], ["Current floor", "1F"], ["Current location", robot.location],
    ["Robot connection", <><span className="robot-info-card__connection-icon">
      <Icon size={15}><path d="M3 8a14 14 0 0 1 18 0M6 12a9 9 0 0 1 12 0m-9 4a4 4 0 0 1 6 0m-3 4h.01"/></Icon>
    </span>Connected</>],
    ["Manufacturer", "Agibot"],
    ["Model", <>{modelName}<small>agibot_g1_description</small></>],
    ["Robot type", robot.id === selected.id ? "Medical robot" : "Cleaning robot"],
    ["Current dispatched task ID", "Unavailable"],
  ];

  return <aside className="robot-inspector" aria-label="Robot Status Information">
    <div className="robot-side-metrics">
      <section className="hmi-gauge energy" aria-label="Battery">
        <div className="gauge-heading"><span>Battery</span><Icon><path d="m13 2-9 12h7l-1 8 10-12h-7z"/></Icon></div>
        <div className="metric-arc battery-arc">
          <div className="battery-liquid" style={{height: `${battery}%`}}/>
          <div className="battery-reading"><strong>{Math.round(battery)}</strong><span>%</span></div>
        </div>
      </section>
      <section className="hmi-gauge thermal" aria-label="Temperature">
        <div className="gauge-heading"><span>Temperature</span><Icon><path d="M10 14.5V5a2 2 0 0 1 4 0v9.5a4 4 0 1 1-4 0z"/></Icon></div>
        <div className="thermal-visual"><div className="thermal-dial">
          <svg className="thermal-dial__scale" viewBox="0 0 160 160" aria-hidden>
            <defs><linearGradient id="thermal-scale-gradient">
              <stop offset="0%" stopColor="#A8DDEB"/><stop offset="38%" stopColor="#EAB7CF"/>
              <stop offset="68%" stopColor="#ED7C84"/><stop offset="100%" stopColor="#F03B38"/>
            </linearGradient></defs>
            <path className="thermal-dial__track" d="M 32 128 A 68 68 0 1 1 128 128"/>
            <path className="thermal-dial__arc" d="M 32 128 A 68 68 0 1 1 128 128"/>
            <circle className="thermal-dial__indicator" cx={80 + 68 * Math.cos(angle)}
              cy={80 + 68 * Math.sin(angle)} r="5"/>
          </svg>
          <strong className="thermal-reading">{Math.round(temperature)}<em>°C</em></strong>
        </div></div>
      </section>
    </div>
    <section className="robot-inspector-content robot-info-card" aria-label="Robot information">
      <header className="robot-info-card__header">
        <h2>Robot information</h2>
        <span className="robot-info-card__state"><i style={{background: "#6f9b7b"}}/>{robot.status}</span>
      </header>
      <dl className="robot-info-card__facts">
        {facts.map(([label, value]) => <div key={label}><dt>{label}</dt>
          <dd className={label === "Robot connection" ? "robot-info-card__connection" : undefined}
            data-state={label === "Robot connection" ? "connected" : undefined}>{value}</dd>
        </div>)}
      </dl>
      <div className="robot-info-card__structure"><h3>Structure</h3>
        <div role="group" aria-label="Structure controls">
          {["Left arm", "Right arm", "Head", "Base", "Whole robot"].map(label =>
            <button key={label} aria-pressed={label === "Whole robot"}>{label}</button>)}
        </div>
      </div>
    </section>
  </aside>;
}

const captions = [
  {from: 15, to: 62, text: "從即時任務追蹤，"},
  {from: 62, to: 113, text: "到機器人車隊管理，"},
  {from: 113, to: 217, text: "MediSync 讓每台機器人的運作狀態與設備資訊，"},
  {from: 217, to: 259, text: "都能清楚掌握。"},
];

export const RobotStatusPhaseV14 = () => {
  const frame = useCurrentFrame();
  const entrance = step(frame, 0, 60);
  const browse = step(frame, 60, 180);
  const reframe = step(frame, 180, 276);
  const robot = frame < selectFrame ? initial : selected;
  const orbit = step(frame, 182, 273);
  const angle = Math.atan2(.588 - .019, 3.093 - .02) - orbit * Math.PI / 2;
  const caption = captions.find(item => frame >= item.from && frame < item.to);
  const mapFade = 1 - step(frame, 3, 27);
  const reveal = step(frame, 7, 25);
  const line = step(frame, 8, 32);
  const frameOpacity = step(frame, 7, 12) * (1 - step(frame, 27, 44));

  return <AbsoluteFill style={{background: "#ecefed", overflow: "hidden"}}>
    {frame < 27 && <Img src={mapPlate} style={{position: "absolute", width: "100%", height: "100%",
      objectFit: "cover", opacity: mapFade}}/>}
    <AbsoluteFill style={{perspective: 2500, perspectiveOrigin: "47% 49%"}}>
      <AbsoluteFill style={{transformStyle: "preserve-3d", transformOrigin: "49% 50%",
        transform: `translate3d(${(18 + 88 * browse) * (1 - reframe) - 22 * Math.sin(reframe * Math.PI)}px,
          ${6 * browse * (1 - reframe)}px, ${(-85 + 70 * browse) * (1 - reframe)}px)
          rotateY(${(-16 + 4 * browse) * (1 - reframe)}deg)
          rotateX(${(7 - 4 * browse) * (1 - reframe)}deg)
          rotateZ(${(-1 + .6 * browse) * (1 - reframe)}deg)`}}>
        <AbsoluteFill style={{transform: `translate3d(${(1 - entrance) * 330}px, ${(1 - entrance) * 134}px, 0)`}}>
          <div className="robot-status-v14" style={{opacity: reveal, boxShadow: "0 22px 65px #48494225"}}>
            <header aria-label="MediSync navigation · Dashboard · Task Dispatch · Schedule History · Live Map · Robot Status"
              style={{height: 76, overflow: "hidden", position: "absolute", inset: "0 0 auto"}}>
              <Img src={nativePage} alt="MediSync navigation" style={{display: "block", width: 1920}}/>
            </header>
            <section className="robot-hmi stage-ready" aria-label="Robot Status">
              <Fleet frame={frame} robot={robot}/>
              <main className="robot-digital-twin-stage">
                <header className="robot-stage-status">
                  <div><strong className="robot-stage-status__name">{robot.id}</strong><span><i data-state="idle"/>{robot.status}</span></div>
                  <p>{modelName} · {robot.location}</p>
                </header>
                <div className="robot-model-cell"><RobotViewport angle={angle}/></div>
              </main>
              <Inspector robot={robot} frame={frame}/>
            </section>
          </div>
          {frame < 44 && <svg width="1920" height="1080" viewBox="0 0 1920 1080"
            style={{position: "absolute", inset: 0, pointerEvents: "none", opacity: frameOpacity}} aria-hidden>
            <path d="M 1 850 V 1 H 1919 V 195" pathLength="1" fill="none" stroke="#f77900" strokeWidth="2"
              strokeDasharray=".25 1" strokeDashoffset={.25 - 1.25 * line}/>
          </svg>}
        </AbsoluteFill>
      </AbsoluteFill>
    </AbsoluteFill>
    {caption && <div lang="zh-Hant" style={{position: "absolute", bottom: 21, left: "50%",
      transform: "translateX(-50%)", whiteSpace: "nowrap", padding: "7px 17px",
      font: "500 27px 'Noto Sans CJK TC', 'Droid Sans Fallback', sans-serif",
      color: "white", background: "#282622eb", borderRadius: 7}}>{caption.text}</div>}
    <Sequence from={12} layout="none">
      <Audio src={staticFile("robot-status-phase-v14/voice.mp3")}/>
    </Sequence>
    <Audio src={staticFile("robot-status-phase-v13/score.wav")} volume={f => .62 * (1 - step(f, 300, 329))}/>
  </AbsoluteFill>;
};
