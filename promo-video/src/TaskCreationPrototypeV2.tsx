import { AbsoluteFill, Audio, Img, staticFile, useCurrentFrame } from "remotion";
import capture from "./task-creation-capture.json";
import route from "./task-creation-route.json";

const p = capture.points;
const asset = (name: string) => staticFile(`task-creation/${name}.png`);
const width = 1600;
const height = 900;
const clamp = (value: number) => Math.max(0, Math.min(1, value));
const ease = (value: number) => {
  const t = clamp(value);
  return t * t * t * (10 + t * (-15 + 6 * t));
};
const mix = (a: number, b: number, t: number) => a + (b - a) * t;
type Pose = readonly [number, number, number];

const wide: Pose = [0, 0, 1];
const form: Pose = [0, -36, 1.22];
const pharmacy: Pose = [-400, -135, 1.25];
const map: Pose = [-215, -6, 1.14];
const submit: Pose = [0, -158, 1.22];
const toast: Pose = [-400, 0, 1.25];
const schedule: Pose = [0, -28, 1.19];

export function taskCamera(frame: number): Pose {
  const move = (from: Pose, to: Pose, start: number, end: number): Pose => {
    const t = ease((frame - start) / (end - start));
    return [mix(from[0], to[0], t), mix(from[1], to[1], t), mix(from[2], to[2], t)];
  };
  if (frame < 127) return move(wide, form, 42, 65);
  if (frame < 193) return move(form, pharmacy, 127, 151);
  if (frame < 292) return map;
  if (frame < 380) return move(submit, wide, 356, 375);
  if (frame < 444) return move(wide, toast, 392, 416);
  return frame < 533 ? schedule : wide;
}

const cursorCues = [
  [10, p.type.x + 100, p.type.y + 35], [72, p.type.x, p.type.y],
  [82, p.type.x, p.type.y], [101, p.medicine.x, p.medicine.y],
  [112, p.medicine.x, p.medicine.y], [157, p.pharmacy.x, p.pharmacy.y],
  [177, p.pharmacy.x, p.pharmacy.y], [193, p.ward.x + 60, p.ward.y + 40],
  [212, p.ward.x, p.ward.y], [225, p.ward.x, p.ward.y],
  [242, p.ward.x + 48, p.ward.y + 45], [292, p.high.x + 75, p.high.y - 34],
  [310, p.high.x, p.high.y], [326, p.high.x, p.high.y],
  [348, p.create.x, p.create.y], [365, p.create.x, p.create.y],
  [444, p.schedule.x + 30, p.schedule.y + 17], [451, p.schedule.x, p.schedule.y],
  [460, p.schedule.x, p.schedule.y], [474, p.edit.x, p.edit.y],
  [482, p.edit.x, p.edit.y], [494, p.time.x, p.time.y],
  [506, p.time.x, p.time.y], [524, p.save.x, p.save.y],
  [533, p.save.x, p.save.y], [534, p.confirm.x + 32, p.confirm.y + 20],
  [543, p.confirm.x, p.confirm.y], [553, p.confirm.x, p.confirm.y],
];
const clicks = [77, 106, 217, 315, 353, 456, 478, 499, 529, 548];
const captions = [
  [7, 115, "任務建立，從視覺化操作開始。"],
  [131, 189, "藥品配送的起點固定為藥局。"],
  [199, 288, "設定目的地，即時預覽路線。"],
  [299, 374, "設定優先級，快速建立任務。"],
  [383, 440, "任務建立成功，狀態即時回饋。"],
  [449, 585, "排程調整，簡單又直觀。"],
] as const;

const states = [
  [0, "initial"], [79, "type-options"], [108, "source-fixed"],
  [219, "route-base"], [271, "route"], [317, "priority"],
  [355, "loading"], [380, "success-base"], [458, "schedule"],
  [480, "edit"], [506, "new-time"], [533, "confirm"], [551, "saved"],
] as const;

const bounce = (frame: number, start: number) => {
  const elapsed = frame - start;
  if (elapsed < 0 || elapsed >= 17) return 0;
  if (elapsed < 6) return -9 * ease(elapsed / 6);
  if (elapsed < 12) return mix(-9, 1.5, ease((elapsed - 6) / 6));
  return mix(1.5, 0, ease((elapsed - 12) / 5));
};

export const TaskCreationPrototypeV2: React.FC = () => {
  const frame = useCurrentFrame();
  const [left, top, scale] = taskCamera(frame);
  const [, state] = [...states].reverse().find(([start]) => frame >= start) ?? states[0];
  const next = cursorCues.findIndex(([time]) => time > frame);
  const before = cursorCues[Math.max(0, next < 0 ? cursorCues.length - 1 : next - 1)];
  const after = cursorCues[next < 0 ? cursorCues.length - 1 : next];
  const travel = ease((frame - before[0]) / Math.max(1, after[0] - before[0]));
  const cursorX = left + scale * mix(before[1], after[1], travel);
  const cursorY = top + scale * mix(before[2], after[2], travel);
  const click = clicks.find((time) => frame >= time && frame < time + 6);
  const press = click === undefined ? 0 : Math.max(0, 1 - Math.abs(frame - click - 2) / 4);
  const caption = captions.find(([start, end]) => frame >= start && frame < end);
  const captionAlpha = caption ? Math.min(ease((frame - caption[0]) / 7), ease((caption[1] - frame) / 7)) : 0;
  const routeIndex = Math.min(route.count - 1, Math.floor((frame - 219) * route.count / 48));
  const sourceMotion = frame >= 159 && frame < 176;
  const destinationMotion = frame >= 219 && frame < 236;
  const displayed = sourceMotion ? "v2-source-clean" : destinationMotion ? "v2-ward-clean" : state;
  const toastMotion = frame - 380;
  const toastScale = toastMotion < 7 ? mix(0.965, 1.012, ease(toastMotion / 7)) :
    mix(1.012, 1, ease((toastMotion - 7) / 8));
  const cursorVisible = (frame >= 10 && frame < 365 && !(frame >= 177 && frame < 193)) ||
    (frame >= 447 && frame < 553);
  const pin = sourceMotion ? p.pharmacy.box : p.ward.box;

  return (
    <AbsoluteFill style={{ backgroundColor: "#f3f4f6", overflow: "hidden" }}>
      <AbsoluteFill style={{ width, height, transformOrigin: "0 0", transform: "scale(1.2)", overflow: "hidden" }}>
        <AbsoluteFill style={{ width, height, transformOrigin: "0 0",
          transform: `translate(${left}px,${top}px) scale(${scale})` }}>
          <Img src={asset(displayed)} style={{ width, height }} />
          {state === "route-base" && <Img src={asset(`route-${routeIndex}`)}
            style={{ position: "absolute", left: route.x, top: route.y, width: route.width, height: route.height }} />}
          {(sourceMotion || destinationMotion) && <Img src={asset(sourceMotion ? "v2-source-pin" : "v2-ward-pin")}
            style={{ position: "absolute", left: Math.floor(pin.x), top: Math.floor(pin.y),
              transform: `translateY(${bounce(frame, sourceMotion ? 159 : 219)}px)` }} />}
          {frame >= 351 && frame < 355 && <div style={{
            position: "absolute", left: p.create.box.x, top: p.create.box.y,
            width: p.create.box.width, height: p.create.box.height, borderRadius: 6,
            background: `rgba(61, 30, 8, ${0.17 * ease((frame - 351) / 3)})`,
          }} />}
          {frame >= 380 && frame < 444 && <Img src={asset("v2-toast")}
            style={{ position: "absolute", left: 1256, top: 73, borderRadius: 12,
              transform: `translateY(${bounce(frame, 380) * 0.34}px) scale(${toastScale})` }} />}
        </AbsoluteFill>
        {cursorVisible && (
          <svg width="19.5" height="21" viewBox="0 0 24 26" style={{
            position: "absolute", left: cursorX, top: cursorY, transformOrigin: "0 0",
            transform: `scale(${1 - 0.14 * press})`, filter: "drop-shadow(0 1px 1px #0006)",
          }}>
            <path d="M1 1v19l5.3-4.6 4.1 8.3 3.8-1.8-4-8.1H18z" fill="#141619" stroke="white" strokeWidth="1.4" />
          </svg>
        )}
      </AbsoluteFill>
      {caption && <div style={{ position: "absolute", bottom: 25, left: 0, right: 0, textAlign: "center",
        opacity: captionAlpha, transform: `translateY(${(1 - captionAlpha) * 6}px)`,
        fontFamily: "'Noto Sans CJK TC', 'Microsoft JhengHei', sans-serif", fontSize: 27, fontWeight: 600 }}>
        <span style={{ backgroundColor: "#18202bea", color: "white", borderRadius: 7, padding: "6px 18px" }}>{caption[2]}</span>
      </div>}
      <Audio src={staticFile("task-creation/v2-score.wav")} />
    </AbsoluteFill>
  );
};
