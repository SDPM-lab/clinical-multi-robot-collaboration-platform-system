import {
  AbsoluteFill,
  Audio,
  Img,
  Sequence,
  staticFile,
  useCurrentFrame,
} from "remotion";
import { ease } from "./DashboardV3Panels";
import captured from "./task-creation-capture.json";
import route from "./task-creation-route.json";
import { captions, sceneFrames as t } from "./task-creation-timing";

const file = (name: string) => staticFile(`task-creation/${name}`);
const width = 1600;
const height = 900;
const points = captured.points;

const shots = [
  [0, "initial"],
  [t.type, "type-options"],
  [t.medicine, "source-fixed"],
  [t.ward, "route-base"],
  [t.high, "priority"],
  [t.create, "loading"],
  [t.success, "success-base"],
  [t.bell, "notification"],
  [t.schedule, "schedule"],
  [t.edit, "edit"],
  [t.time + 8, "new-time"],
  [t.save, "confirm"],
  [t.saved, "saved"],
] as const;

const actions = [
  [t.type, points.type],
  [t.medicine, points.medicine],
  [t.pharmacy, points.pharmacy],
  [t.ward, points.ward],
  [t.high, points.high],
  [t.create, points.create],
  [t.bell, points.bell],
  [t.schedule, points.schedule],
  [t.edit, points.edit],
  [t.time, points.time],
  [t.save, points.save],
  [t.confirm, points.confirm],
] as const;

const mix = (a: number, b: number, p: number) => a + (b - a) * p;

export const TaskCreationPrototype = ({
  voiceover,
}: {
  voiceover?: string;
}) => {
  const f = useCurrentFrame();
  const shot = shots.reduce<(typeof shots)[number][1]>(
    (name, [at, capture]) => (at <= f ? capture : name),
    "initial",
  );
  const caption = captions.find((c) => c.start <= f && f < c.end);
  const next = actions.findIndex(([at]) => at > f);
  const actionIndex = next < 0 ? actions.length - 1 : Math.max(0, next - 1);
  const previousCursor =
    f < actions[0][0] ? { x: 500, y: 390 } : actions[actionIndex][1];
  const target = actions[next < 0 ? actionIndex : next];
  const journey = ease(
    f,
    Math.max(next <= 0 ? 30 : actions[actionIndex][0] + 5, target[0] - 28),
    target[0] - 4,
  );
  const pointer = {
    x: mix(previousCursor.x, target[1].x, journey),
    y:
      mix(previousCursor.y, target[1].y, journey) -
      Math.sin(Math.PI * journey) * 19,
  };
  const press = actions.some(
    ([at]) => at !== t.pharmacy && f >= at - 2 && f <= at + 2,
  );
  const orbit = ease(f, 4, 58);
  const map = ease(f, 107, 166) * (1 - ease(f, 252, 290));
  const toast = ease(f, t.success, t.success + 17) * (1 - ease(f, 387, 404));
  const schedule = ease(f, 404, 425) * (1 - ease(f, 471, 485));
  const form =
    ease(f, 40, 67) * (1 - ease(f, 104, 126)) +
    ease(f, 282, 315) * (1 - ease(f, 337, 355));
  const scale =
    1.105 + 0.19 * form + 0.14 * map + 0.26 * toast + 0.28 * schedule;
  const offsetX =
    (1920 - width * scale) / 2 +
    (94 * form + 14 * map - 148 * toast + 137 * schedule);
  const offsetY = Math.max(
    0,
    (1080 - height * scale) / 2 + 61 * toast + 20 * schedule,
  );
  const frameOfRoute = Math.min(
    route.count - 1,
    Math.floor(ease(f, t.ward, t.ward + 55) * route.count),
  );
  const successMotion = f - t.success;
  const pop = ease(f, t.success, t.success + 8);
  const bounce = Math.sin(successMotion * 0.58) * Math.exp(-successMotion / 7);
  const box = points.toast.box;
  return (
    <AbsoluteFill
      style={{
        background: "#f5f3ee",
        overflow: "hidden",
        fontFamily: "Arial, 'Noto Sans CJK TC', sans-serif",
      }}
    >
      <Audio src={file("score.wav")} volume={0.8} />
      {voiceover && (
        <Sequence from={5} layout="none">
          <Audio src={file(voiceover)} volume={0.89} />
        </Sequence>
      )}
      <AbsoluteFill style={{ perspective: 2300 }}>
        <div
          style={{
            position: "absolute",
            left: offsetX,
            top: offsetY,
            width,
            height,
            transformOrigin: "0 0",
            transform: `scale(${scale}) translateX(${26 * (1 - orbit)}px) rotateY(${-6 * (1 - orbit)}deg) rotateX(${3 * (1 - orbit)}deg)`,
            transformStyle: "preserve-3d",
            boxShadow: "0 15px 56px #28231b24",
          }}
        >
          <Img
            src={file(f < 58 ? "opening-map.png" : shot + ".png")}
            width={width}
            height={height}
            style={{ position: "absolute", inset: 0 }}
          />
          {shot === "route-base" && (
            <Img
              src={file(`route-${frameOfRoute}.png`)}
              width={route.width}
              height={route.height}
              style={{ position: "absolute", left: route.x, top: route.y }}
            />
          )}
          {f < 58 && (
            <div
              style={{
                position: "absolute",
                left: 24,
                top: 100,
                width: 416,
                height: 620,
                overflow: "hidden",
                borderRadius: 16,
                transform: `translate3d(${-38 * (1 - orbit)}px,${15 * (1 - orbit)}px,${106 * (1 - orbit)}px) rotateY(${-10 * (1 - orbit)}deg)`,
                boxShadow: `0 18px 44px rgba(49,45,38,${0.19 * (1 - orbit)})`,
                opacity: 1 - ease(f, 51, 58),
              }}
            >
              <Img
                src={file("initial.png")}
                width={width}
                height={height}
                style={{ position: "absolute", left: -24, top: -100 }}
              />
            </div>
          )}
          {shot === "success-base" && (
            <div
              style={{
                position: "absolute",
                left: box.x,
                top: box.y,
                width: box.width,
                height: box.height,
                overflow: "hidden",
                borderRadius: 8,
                transformOrigin: "90% 12%",
                transform: `translateX(${bounce * 1.8}px) scale(${0.96 + 0.04 * pop + 0.023 * bounce})`,
              }}
            >
              <Img
                src={file("success.png")}
                width={width}
                height={height}
                style={{ position: "absolute", left: -box.x, top: -box.y }}
              />
            </div>
          )}
          {f >= t.create - 3 && f < t.create && (
            <div
              style={{
                position: "absolute",
                left: points.create.box.x,
                top: points.create.box.y,
                width: points.create.box.width,
                height: points.create.box.height,
                borderRadius: 5,
                background: "#67411c28",
              }}
            />
          )}
          {f >= 30 && f < 511 && (
            <svg
              viewBox="0 0 32 43"
              width={31}
              height={42}
              style={{
                position: "absolute",
                left: pointer.x,
                top: pointer.y,
                filter: "drop-shadow(1px 2px 2px #19171555)",
                transform: `scale(${press ? 0.84 : 1})`,
                transformOrigin: "0% 0%",
                pointerEvents: "none",
              }}
            >
              <path
                d="M3 2 L3 34 L11 26 L17 40 L22 38 L16 24 L29 24 Z"
                fill="#25221e"
                stroke="#fff"
                strokeWidth="2.4"
                strokeLinejoin="round"
              />
            </svg>
          )}
        </div>
      </AbsoluteFill>
      {caption && (
        <div
          style={{
            position: "absolute",
            bottom: 24,
            width: "100%",
            textAlign: "center",
            fontSize: 36,
          }}
        >
          <span
            style={{
              display: "inline-block",
              color: "white",
              background: "#272019",
              borderRadius: 5,
              padding: "7px 17px",
            }}
          >
            {caption.text}
          </span>
        </div>
      )}
    </AbsoluteFill>
  );
};
