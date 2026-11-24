import {
  Easing,
  Img,
  interpolate,
  staticFile,
  useCurrentFrame,
} from "remotion";
import chart from "./dashboard-v5-chart.json";
import metrics from "./dashboard-v5-metrics.json";
import demo from "./dashboard-v5-demo.json";
import { ease } from "./DashboardV3Panels";

const asset = (name: string) => staticFile(`dashboard-v5/${name}`);
const chartWidth = 943;
const chartHeight = 293;

export const BatteryGrowthV5 = () => {
  const frame = useCurrentFrame();
  const floorRanks = [0, 0, 0];
  return (
    <svg
      viewBox={`0 0 ${chartWidth} ${chartHeight}`}
      width={chartWidth}
      height={chartHeight}
      style={{ display: "block" }}
    >
      <defs>
        <clipPath id="v5-growing-bars">
          {chart.bars.map((box, index) => {
            const start = 172 + box.floor * 3 + 2 * floorRanks[box.floor]++;
            const height = interpolate(frame, [start, start + 22], [0, box.h], {
              easing: Easing.out(Easing.cubic),
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            return (
              <rect
                key={index}
                x={box.x}
                y={box.y + box.h - height}
                width={box.w}
                height={height}
              />
            );
          })}
        </clipPath>
      </defs>
      <image
        href={asset("battery-empty.png")}
        width={chartWidth}
        height={chartHeight}
        preserveAspectRatio="none"
      />
      <image
        href={asset("battery.png")}
        width={chartWidth}
        height={chartHeight}
        preserveAspectRatio="none"
        clipPath="url(#v5-growing-bars)"
      />
    </svg>
  );
};

export const NetworkV5 = () => {
  const frame = useCurrentFrame();
  const { wifi, orange } = metrics;
  const arcs = [
    "M24 34 Q32 27 40 34",
    "M15 25 Q32 10 49 25",
    "M7 16 Q32 -5 57 16",
  ];
  const brightness = (start: number) =>
    0.24 + 0.76 * ease(frame, start, start + 10);
  return (
    <>
      <Img
        src={asset("network-empty.png")}
        width={239}
        height={140}
        style={{ display: "block" }}
      />
      <svg
        viewBox="0 0 64 48"
        style={{
          position: "absolute",
          left: wifi.x,
          top: wifi.y,
          width: wifi.w,
          height: wifi.h,
          overflow: "visible",
        }}
      >
        {arcs.map((d, index) => (
          <path
            key={d}
            d={d}
            stroke={orange}
            fill="none"
            strokeWidth="2.5"
            strokeLinecap="round"
            opacity={brightness(231 + index * 5)}
          />
        ))}
        <circle cx="32" cy="42" r="2" fill={orange} opacity={brightness(225)} />
      </svg>
    </>
  );
};

export const FleetCountV5 = () => {
  const f = useCurrentFrame();
  const total = demo.robots.length;
  const connected = demo.robots.filter((robot) => robot.connected).length;
  const count = Math.min(connected, Math.max(0, Math.floor((f - 189) / 4)));
  const { count: box, caption } = metrics.fleet;
  return (
    <>
      <Img
        src={asset("fleet-empty.png")}
        width={239}
        height={140}
        style={{ display: "block" }}
      />
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: box.y,
          height: box.h,
          display: "flex",
          justifyContent: "center",
          alignItems: "baseline",
          gap: 8,
          fontVariantNumeric: "tabular-nums",
        }}
      >
        <span style={{ fontSize: 38, color: "#f19a68" }}>{count}</span>
        <span style={{ fontSize: 20, color: "#686965" }}>/ {total}</span>
      </div>
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: caption.y,
          height: caption.h,
          textAlign: "center",
          color: "#686965",
          fontSize: 11,
        }}
      >
        {count} robots connected
      </div>
    </>
  );
};
