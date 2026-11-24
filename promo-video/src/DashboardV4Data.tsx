import { Img, staticFile, useCurrentFrame } from "remotion";
import { ease } from "./DashboardV3Panels";
import demo from "./dashboard-v4-demo.json";
import chart from "./dashboard-v4-chart.json";
import gauge from "./dashboard-v4-gauge.json";

const file = (name: string) => staticFile(`dashboard-v4/${name}`);
export const BatteryAnimation = () => {
  const frame = useCurrentFrame();
  return (
    <>
      <Img src={file("battery-empty.png")} width={943} height={293} />
      {chart.bars.map((box, index) => {
        const start = 176 + Math.floor(index / 7) * 3 + (index % 7);
        const growth = ease(frame, start, start + 26);
        return (
          <div
            key={index}
            style={{
              position: "absolute",
              left: box.x,
              top: box.y,
              width: box.w,
              height: box.h,
              transform: `scaleY(${growth})`,
              transformOrigin: "center bottom",
              overflow: "hidden",
            }}
          >
            <Img
              src={file("battery.png")}
              width={943}
              height={293}
              style={{
                position: "absolute",
                left: -box.x,
                top: -box.y,
              }}
            />
          </div>
        );
      })}
      {chart.legend.map((box, index) => {
        const p =
          ease(frame, 205 + index * 2, 211 + index * 2) *
          (1 - ease(frame, 211 + index * 2, 218 + index * 2));
        return (
          <div
            key={index}
            style={{
              position: "absolute",
              left: box.x - 3,
              top: box.y - 2,
              width: box.w + 6,
              height: box.h + 4,
              borderRadius: 3,
              background: "#faac5c",
              opacity: p * 0.18,
            }}
          />
        );
      })}
    </>
  );
};

export const CompletionSweep = ({
  start = 153,
  end = 211,
  target = demo.completion,
}: {
  start?: number;
  end?: number;
  target?: number;
}) => {
  const frame = useCurrentFrame();
  const value = target * ease(frame, start, end);
  const { dial, completion } = gauge;
  return (
    <>
      <Img src={file("gauge-empty.png")} width={340} height={326} />
      <svg
        viewBox="0 0 240 142"
        style={{
          position: "absolute",
          left: dial.x,
          top: dial.y,
          width: dial.w,
          height: dial.h,
        }}
      >
        <defs>
          <linearGradient id="v4-dial-arc">
            <stop offset="0%" stopColor="#f19366" />
            <stop offset="58%" stopColor="#f19366" />
            <stop offset="100%" stopColor="#ffcd5f" />
          </linearGradient>
        </defs>
        {value > 0 && (
          <path
            d="M27 108 A93 93 0 0 1 213 108"
            pathLength="100"
            strokeDasharray={`${value} 100`}
            stroke="url(#v4-dial-arc)"
            strokeLinecap="round"
            strokeWidth="9"
            fill="none"
          />
        )}
        <path
          d="M117.5 108 L120 35 L122.5 108 Z"
          transform={`rotate(${-90 + value * 1.8} 120 108)`}
          fill={completion.needle}
        />
        <circle cx="120" cy="108" r="5" fill={completion.needle} />
        <text
          x="120"
          y="87"
          textAnchor="middle"
          fontSize="35"
          fill={completion.ink}
        >
          {Math.round(value)}
        </text>
      </svg>
    </>
  );
};

export const FleetCount = () => {
  const frame = useCurrentFrame();
  const total = demo.robots.length;
  const count = Math.min(total, Math.max(0, Math.floor((frame - 180) / 7)));
  const { number, caption } = gauge.fleet;
  return (
    <>
      <Img
        src={staticFile("dashboard-v3/fleet.png")}
        width={239}
        height={140}
      />
      {count < total && (
        <>
          <div
            style={{
              position: "absolute",
              left: number.x - 2,
              top: number.y,
              width: number.w + 4,
              height: number.h,
              display: "grid",
              placeItems: "center",
              background: "#fafbfa",
              color: "#f19a68",
              fontSize: 38,
              lineHeight: 1,
            }}
          >
            {count}
          </div>
          <div
            style={{
              position: "absolute",
              left: caption.x - 4,
              top: caption.y,
              width: caption.w + 8,
              height: caption.h,
              textAlign: "center",
              background: "#fafbfa",
              color: "#686965",
              fontSize: 11,
            }}
          >
            {count} robots connected
          </div>
        </>
      )}
    </>
  );
};

export const ProgressMotion = ({
  progress = demo.progress,
}: {
  progress?: typeof demo.progress;
}) => {
  const frame = useCurrentFrame();
  const stops = [88, 136, 184];
  const segments = progress
    .slice(1)
    .map((stop, index) => ease(frame, progress[index].frame, stop.frame));
  if (frame < progress[0].frame) return null;
  return (
    <svg
      viewBox="0 0 350 293"
      style={{
        width: 350,
        height: 293,
        position: "absolute",
        inset: 0,
        pointerEvents: "none",
      }}
    >
      {segments.map((p, index) => (
        <path
          key={index}
          d={`M31 ${stops[index]} V${stops[index] + 48 * p}`}
          stroke="#e98246"
          strokeWidth="2"
        />
      ))}
      {progress.map((step, index) => {
        if (frame < step.frame) return null;
        const pulse =
          ease(frame, step.frame, step.frame + 5) *
          (1 - ease(frame, step.frame + 5, step.frame + 13));
        return (
          <g key={step.state}>
            <circle
              cx="31"
              cy={stops[index]}
              r={11 + 3 * pulse}
              fill="#faf9f6"
              stroke="#ea8549"
              strokeWidth="2"
            />
            <circle
              cx="31"
              cy={stops[index]}
              r={index === 2 ? 5 : 4}
              fill="#e98246"
            />
          </g>
        );
      })}
    </svg>
  );
};
