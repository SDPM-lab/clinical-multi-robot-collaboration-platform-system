import { AbsoluteFill, Audio, Img, Sequence, staticFile, useCurrentFrame } from "remotion";
import type { CSSProperties, ReactNode } from "react";
import capture from "./task-creation-capture.json";
import path from "./task-creation-v3-route.json";

const points = capture.points;
const demo = capture.task;
const asset = (name: string) => staticFile(`task-creation/${name}.png`);
const paper = "#faf7f2";
const ease = (f: number, start: number, end: number) => {
  const t = Math.min(1, Math.max(0, (f - start) / (end - start)));
  return t * t * (3 - 2 * t);
};
const mix = (a: number, b: number, t: number) => a + (b - a) * t;

type Rect = readonly [number, number, number, number];
const form: Rect = [24, 100, 416, 620];
const map: Rect = [483, 79, 1095, 618];
const priority: Rect = [32, 470, 400, 65];
const create: Rect = [248, 645, 184, 64];
const dialog: Rect = [560, 333, 480, 234];
const row: Rect = [37, 268, 393, 68];

const Capture = ({ name, crop, x, y, scale, children, style }: {
  name: string; crop: Rect; x: number; y: number; scale: number; children?: ReactNode; style?: CSSProperties;
}) => {
  const [left, top, width, height] = crop;
  return <div style={{ position: "absolute", left: x, top: y, width: width * scale,
    height: height * scale, overflow: "hidden", ...style }}>
    <div style={{ position: "absolute", left: -left * scale, top: -top * scale,
      width: 1600, height: 900, transformOrigin: "0 0", transform: `scale(${scale})` }}>
      <Img src={asset(name)} style={{ position: "absolute", width: 1600, height: 900 }} />
      {children}
    </div>
  </div>;
};

const Stage = ({ children }: { children: ReactNode }) =>
  <AbsoluteFill style={{ background: paper, color: "#231d19", overflow: "hidden",
    fontFamily: "Arial, 'Noto Sans CJK TC', sans-serif" }}>{children}</AbsoluteFill>;

const Label = ({ children, x, y, size = 47 }: { children: ReactNode; x: number; y: number; size?: number }) =>
  <div style={{ position: "absolute", left: x, top: y, fontSize: size, fontWeight: 750,
    letterSpacing: -size * .045, lineHeight: 1.05 }}>{children}</div>;

const Cursor = ({ f, x, y, click }: { f: number; x: number; y: number; click: number }) => {
  const press = Math.max(0, 1 - Math.abs(f - click - 2) / 4);
  return <svg viewBox="0 0 24 26" width={22} height={24} style={{ position: "absolute",
    left: x, top: y, transformOrigin: "0 0", transform: `scale(${1 - press * .15})`,
    filter: "drop-shadow(0 1px 1px #0008)" }}>
    <path d="M1 1v19l5.3-4.6 4.1 8.3 3.8-1.8-4-8.1H18z" fill="#191817" stroke="white" strokeWidth="1.4" />
  </svg>;
};

const ShotFormExtraction = () => {
  const f = useCurrentFrame();
  const move = ease(f, 9, 48);
  const quiet = ease(f, 9, 30);
  return <Stage>
    <Img src={asset("opening-map")} style={{ width: 1920, height: 1080, opacity: 1 - quiet }} />
    <Capture name="initial" crop={form} x={mix(28.8, 673, move)} y={mix(120, 88, move)}
      scale={mix(1.2, 1.38, move)} style={{ borderRadius: 16,
        boxShadow: `0 ${mix(0, 24, quiet)}px ${mix(0, 64, quiet)}px rgba(65,47,29,${quiet * .2})` }} />
  </Stage>;
};

const ShotTaskType = () => {
  const f = useCurrentFrame();
  const move = ease(f, 0, 15);
  const x = mix(673, 1060, move);
  const y = 88;
  const s = 1.38;
  const press = f < 42 ? 29 : 52;
  const target = f < 37 ? points.type : points.medicine;
  const travel = f < 37 ? ease(f, 16, 25) : ease(f, 37, 47);
  return <Stage>
    <div style={{ opacity: move, transform: `translateY(${(1 - move) * 12}px)` }}>
      <Label x={160} y={358} size={125}>Create.<br /><span style={{ color: "#d85912" }}>Simply.</span></Label>
    </div>
    <Capture name={f < 31 ? "initial" : f < 54 ? "type-options" : "source-fixed"} crop={form}
      x={x} y={y} scale={s} style={{ borderRadius: 16, boxShadow: "0 24px 64px #412f1d33" }} />
    {f >= 16 && f < 62 && <Cursor f={f} click={press}
      x={x + (target.x - form[0] + 55 * (1 - travel)) * s}
      y={y + (target.y - form[1] + 38 * (1 - travel)) * s} />}
  </Stage>;
};

const ShotFloorMap = () => {
  const f = useCurrentFrame();
  const land = ease(f, 0, 16);
  const x = 100;
  const y = 88;
  const s = 1.57;
  const source = f < 47;
  const pinStart = source ? 30 : 64;
  const marker = source ? points.pharmacy : points.ward;
  const motion = ease(f, pinStart, pinStart + 5) * (1 - ease(f, pinStart + 5, pinStart + 15));
  const flying = f >= pinStart && f < pinStart + 15;
  const progress = ease(f, 66, 106);
  const hover = source ? ease(f, 22, 28) : ease(f, 50, 58);
  return <Stage>
    <div style={{ position: "absolute", inset: 0, perspective: 1800,
      clipPath: `inset(0 ${(1 - land) * 18}% 0 ${(1 - land) * 18}%)` }}>
      <div style={{ position: "absolute", inset: 0, transform: `rotateX(${-7 * (1 - land)}deg) translateY(${35 * (1 - land)}px)` }}>
        <Capture name={flying ? source ? "v2-source-clean" : "v2-ward-clean" : "route-base"} crop={map}
          x={x} y={y} scale={s} style={{ borderRadius: 18, boxShadow: "0 22px 55px #5a412528" }}>
          {progress > 0 && <svg width={1600} height={900} style={{ position: "absolute", inset: 0 }}>
            <path d={path.d} pathLength={1} fill="none" stroke={path.color}
              strokeWidth={path.width} strokeLinecap="round" strokeLinejoin="round"
              strokeDasharray="1 1" strokeDashoffset={1 - progress} />
          </svg>}
          {flying && <Img src={asset(source ? "v2-source-pin" : "v2-ward-pin")} style={{ position: "absolute",
            left: Math.floor(marker.box.x), top: Math.floor(marker.box.y),
            transformOrigin: "50% 95%", transform: `translateY(${-9 * motion}px) scale(${1 + .04 * motion})` }} />}
        </Capture>
      </div>
    </div>
    <Label x={108} y={32} size={32}>{f < 64 ? "Pharmacy · Fixed Source" : "Pharmacy → Ward A"}</Label>
    {((f >= 22 && f < 41) || (f >= 50 && f < 77)) && <Cursor f={f} click={source ? -30 : 62}
      x={x + (marker.x - map[0] + 34 * (1 - hover)) * s}
      y={y + (marker.y - map[1] + 38 * (1 - hover)) * s} />}
  </Stage>;
};

const ShotPriorityCreate = () => {
  const f = useCurrentFrame();
  const isPriority = f < 28;
  const target = isPriority ? points.high : points.create;
  const crop = isPriority ? priority : create;
  const x = isPriority ? 360 : 514;
  const y = isPriority ? 450 : 421;
  const s = isPriority ? 3 : 4.85;
  const click = isPriority ? 15 : 42;
  const hover = ease(f, click - 11, click - 4);
  return <Stage>
    <Label x={x} y={298} size={76}>{isPriority ? "Set the priority." : "Create the task."}</Label>
    <Capture name={isPriority && f < 17 ? "route" : f >= 44 ? "loading" : "priority"} crop={crop}
      x={x} y={y} scale={s} style={{ borderRadius: 18, boxShadow: "0 22px 58px #5a412526" }}>
      {!isPriority && f >= 42 && f < 44 && <div style={{ position: "absolute", left: target.box.x,
        top: target.box.y, width: target.box.width, height: target.box.height, background: "#53301932", borderRadius: 5 }} />}
    </Capture>
    {(isPriority || f < 48) && <Cursor f={f} click={click}
      x={x + (target.x - crop[0]) * s + 72 * (1 - hover)}
      y={y + (target.y - crop[1]) * s + 52 * (1 - hover)} />}
  </Stage>;
};

const ShotNotification = () => {
  const f = useCurrentFrame();
  const slide = ease(f, 0, 25);
  const pulse = 1 + .044 * ease(f, 22, 27) * (1 - ease(f, 27, 36));
  return <Stage>
    <div style={{ opacity: ease(f, 16, 31) }}><Label x={300} y={282} size={85}>Task created.</Label></div>
    <div style={{ position: "absolute", left: mix(1420, 300, slide), top: mix(107, 432, slide),
      transform: `scale(${pulse})`, transformOrigin: "50% 50%", overflow: "hidden", borderRadius: 27,
      width: mix(370, 1320, slide), aspectRatio: "322 / 54", boxShadow: "0 25px 65px #28483326" }}>
      <Img src={asset("v2-toast")} style={{ width: "100%", height: "100%" }} />
    </div>
    {f >= 63 && <div style={{ position: "absolute", left: 300, top: 708, fontSize: 48,
      fontWeight: 750, color: "#9b481c", opacity: ease(f, 63, 74) }}>{demo.taskCode}</div>}
  </Stage>;
};

const ShotSchedule = () => {
  const f = useCurrentFrame();
  const landing = ease(f, 0, 12);
  const edit = f >= 22;
  const confirming = f >= 50 && f < 67;
  const saved = f >= 67;
  const crop = confirming ? dialog : saved ? row : form;
  const x = confirming ? 470 : saved ? 650 : 666;
  const y = confirming ? 310 : saved ? mix(268, 452, ease(f, 67, 78)) : 80;
  const s = confirming ? 2.02 : saved ? 1.8 : 1.42;
  const target = confirming ? points.confirm : f < 22 ? points.edit : f < 38 ? points.time : points.save;
  const click = confirming ? 64 : f < 22 ? 20 : f < 38 ? 32 : 48;
  const hover = ease(f, click - 8, click - 3);
  return <Stage>
    {!confirming && <Label x={107} y={259} size={66}>Schedule<br />with <span style={{ color: "#ce5718" }}>flexibility.</span></Label>}
    <div style={{ position: "absolute", left: 300, top: mix(708, 430, landing), color: "#9b481c",
      fontSize: 48, fontWeight: 750 }}>{demo.taskCode}</div>
    {saved && <Label x={648} y={343} size={68}>14:20 <span style={{ color: "#ce5718" }}>→ 15:05</span></Label>}
    <Capture name={saved ? "saved" : confirming ? "confirm" : f >= 38 ? "new-time" : edit ? "edit" : "schedule"}
      crop={crop} x={x} y={y} scale={s} style={{ borderRadius: 15, boxShadow: "0 20px 55px #553a242a",
        opacity: confirming || saved ? 1 : landing, transform: saved || confirming ? undefined :
          `perspective(1200px) rotateX(${(1 - landing) * -9}deg) translateY(${(1 - landing) * -60}px)` }} />
    {f >= 12 && !saved && <Cursor f={f} click={click}
      x={x + (target.x - crop[0]) * s + 23 * (1 - hover)}
      y={y + (target.y - crop[1]) * s + 29 * (1 - hover)} />}
  </Stage>;
};

const shots = [
  [0, 60, ShotFormExtraction], [60, 75, ShotTaskType], [135, 120, ShotFloorMap],
  [255, 60, ShotPriorityCreate], [315, 75, ShotNotification], [390, 90, ShotSchedule],
] as const;

const lines = [
  [8, 79, "讓任務建立，更直觀。"],
  [98, 224, "透過視覺化地圖，即時規劃配送路線。"],
  [245, 329, "從任務建立到彈性排程，"],
  [352, 444, "繁複的流程，只需簡單操作。"],
] as const;

export type TaskCreationV3Props = { voiceover?: string };
export const TaskCreationPrototypeV3 = ({ voiceover }: TaskCreationV3Props) => {
  const f = useCurrentFrame();
  const caption = lines.find(([from, to]) => f >= from && f < to);
  return <AbsoluteFill>
    {shots.map(([start, duration, Shot]) =>
      <Sequence key={start} from={start} durationInFrames={duration}><Shot /></Sequence>)}
    {caption && <div style={{ position: "absolute", bottom: 30, left: 0, right: 0, textAlign: "center",
      fontFamily: "'Noto Sans CJK TC', sans-serif", fontWeight: 700, fontSize: 31,
      opacity: ease(f, caption[0], caption[0] + 5) * (1 - ease(f, caption[1] - 5, caption[1])) }}>
      <span style={{ background: "#241e1bed", color: "white", borderRadius: 7, padding: "6px 17px" }}>{caption[2]}</span>
    </div>}
    <Audio src={staticFile("task-creation/v3-score.wav")} volume={voiceover ? .73 : 1} />
    {voiceover && <Audio src={staticFile(voiceover)} volume={.92} />}
  </AbsoluteFill>;
};
