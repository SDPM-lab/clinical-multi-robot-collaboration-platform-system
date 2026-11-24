import { Img, staticFile, useCurrentFrame } from "remotion";
import { ease } from "./DashboardV3Panels";
import data from "./dashboard-v3-demo.json";

type Name = "schedule" | "gauge" | "network" | "fleet" | "battery" | "progress";

export const NativePanel = ({
  name,
  width,
  height,
}: {
  name: Name;
  width: number;
  height: number;
}) => {
  const frame = useCurrentFrame();
  const glow = 1 - ease(frame, 188, 214);
  const connected = data.robots.filter((robot) => robot.connected).length;
  const count = Math.round(connected * ease(frame, 165, 192));
  const completed = Math.round(data.completion * ease(frame, 119, 160));

  return (
    <>
      <Img
        src={staticFile(`dashboard-v3/${name}.png`)}
        width={width}
        height={height}
        style={{ display: "block" }}
      />
      {name === "schedule" &&
        Array.from({ length: 5 }, (_, index) => {
          const amount = ease(frame, 108 + index * 7, 124 + index * 7);
          return (
            <div
              key={index}
              style={{
                position: "absolute",
                left: 15,
                right: 13,
                top: 135 + index * 58,
                height: 54,
                background: "#f9faf9",
                opacity: 1 - amount,
                transformOrigin: "right center",
                transform: `scaleX(${1 - amount * 0.12})`,
              }}
            />
          );
        })}
      {name === "progress" &&
        Array.from({ length: 3 }, (_, index) => (
          <div
            key={index}
            style={{
              position: "absolute",
              left: 10,
              right: 9,
              top: 72 + index * 48,
              height: 44,
              background: "#f9faf9",
              opacity: 1 - ease(frame, 189 + index * 7, 205 + index * 7),
            }}
          />
        ))}
      {name === "battery" &&
        [0, 1, 2].map((index) => (
          <div
            key={index}
            style={{
              position: "absolute",
              left: 32 + (index * (width - 38)) / 3,
              width: (width - 50) / 3,
              top: 88,
              height: 145,
              background: "linear-gradient(#fffefcdd,#fffefcf8)",
              transformOrigin: "top",
              transform: `scaleY(${1 - ease(frame, 172 + index * 10, 200 + index * 10)})`,
            }}
          />
        ))}
      {name === "network" && (
        <svg
          viewBox="0 0 72 58"
          width="58"
          height="45"
          style={{
            position: "absolute",
            left: width / 2 - 29,
            top: 43,
            opacity: ease(frame, 149, 159) * glow,
          }}
        >
          {[
            "M27 36Q36 29 45 36",
            "M16 26Q36 12 56 26",
            "M7 16Q36 -5 65 16",
          ].map((d, index) => (
            <path
              key={d}
              d={d}
              pathLength="1"
              fill="none"
              stroke="#f28a42"
              strokeWidth="3"
              strokeLinecap="round"
              strokeDasharray=".16 1"
              strokeDashoffset={
                1 - ease(frame, 151 + index * 5, 177 + index * 5)
              }
            />
          ))}
        </svg>
      )}
      {name === "fleet" && frame < 192 && (
        <div
          style={{
            position: "absolute",
            left: width / 2 - 43,
            top: 48,
            width: 38,
            height: 44,
            font: "38px Arial",
            color: "#ed9766",
            background: "#f7f8f7",
            textAlign: "center",
          }}
        >
          {count}
        </div>
      )}
      {name === "gauge" && frame < 160 && (
        <div
          style={{
            position: "absolute",
            left: width / 2 - 30,
            top: 132,
            width: 60,
            height: 39,
            font: "42px Arial",
            color: "#35332a",
            background: "linear-gradient(#fff3c8,#fff2c3)",
            textAlign: "center",
          }}
        >
          {completed}
        </div>
      )}
    </>
  );
};
