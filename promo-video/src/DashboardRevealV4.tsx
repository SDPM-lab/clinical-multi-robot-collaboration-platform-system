import {
  AbsoluteFill,
  Audio,
  Img,
  Sequence,
  staticFile,
  useCurrentFrame,
} from "remotion";
import { ease, PanelPlane } from "./DashboardV3Panels";
import { NativePanel } from "./DashboardV3NativePanel";
import {
  BatteryAnimation,
  CompletionSweep,
  FleetCount,
  ProgressMotion,
} from "./DashboardV4Data";
import captions from "./dashboard-v4-captions.json";
import layout from "./dashboard-v3-layout.json";

const panels = [
  {
    name: "schedule",
    start: 117,
    dx: 158,
    dy: -6,
    z: -190,
    rx: 4,
    ry: -27,
    origin: "100% 45%",
  },
  {
    name: "gauge",
    start: 128,
    dx: -96,
    dy: 0,
    z: 150,
    rx: -12,
    ry: 24,
    origin: "0% 70%",
  },
  {
    name: "network",
    start: 139,
    dx: -116,
    dy: 48,
    z: -172,
    rx: 24,
    ry: 17,
    origin: "0% 100%",
  },
  {
    name: "fleet",
    start: 147,
    dx: -121,
    dy: 78,
    z: -123,
    rx: 26,
    ry: 17,
    origin: "0% 100%",
  },
  {
    name: "battery",
    start: 155,
    dx: -20,
    dy: 153,
    z: 140,
    rx: -29,
    ry: -6,
    origin: "50% 100%",
  },
  {
    name: "progress",
    start: 165,
    dx: 136,
    dy: 106,
    z: -182,
    rx: 24,
    ry: -24,
    origin: "100% 90%",
  },
] as const;

export type DashboardV4Props = { voiceover?: string };

export const DashboardRevealV4 = ({ voiceover }: DashboardV4Props) => {
  const f = useCurrentFrame();
  const exit = ease(f, 60, 93);
  const camera = ease(f, 65, 195);
  const screen = ease(f, 72, 119);
  const cue = captions.find((line) => f >= line.start && f < line.end);
  return (
    <AbsoluteFill
      style={{
        fontFamily: "Arial, Helvetica, 'Noto Sans CJK TC', sans-serif",
        color: "#23201d",
        background: "radial-gradient(ellipse at 65% 48%,#fff 28%,#f5f1ea 100%)",
        overflow: "hidden",
      }}
    >
      <Audio src={staticFile("dashboard-v4/mix.wav")} volume={0.64} />
      {voiceover && (
        <Sequence from={6} layout="none">
          <Audio src={staticFile(voiceover)} volume={0.95} />
        </Sequence>
      )}
      <AbsoluteFill
        style={{
          perspective: 1950,
          perspectiveOrigin: "50% 48%",
          opacity: screen,
        }}
      >
        <div
          style={{
            position: "absolute",
            left: 160,
            top: 44,
            width: 1600,
            height: 900,
            transformStyle: "preserve-3d",
            transform: `translate3d(${32 * (1 - camera)}px,${65 * (1 - camera)}px,${-125 * (1 - camera)}px) rotateX(${7 * (1 - camera)}deg) rotateY(${-9 * (1 - camera)}deg) scale(1.055)`,
          }}
        >
          <Img
            src={staticFile("dashboard-v4/wide-base.png")}
            width={1600}
            height={900}
            style={{
              position: "absolute",
              borderRadius: 0,
              boxShadow: "0 14px 46px #513c241f",
              transform: "translateZ(-208px) scale(1.1067)",
            }}
          />
          {panels.map(({ name, ...motion }) => {
            const { x, y, width, height } = layout[name];
            return (
              <PanelPlane
                key={name}
                x={x}
                y={y}
                w={width}
                h={height}
                shadowFollowsDepth
                {...motion}
              >
                {name === "battery" ? (
                  <BatteryAnimation />
                ) : name === "gauge" ? (
                  <CompletionSweep />
                ) : name === "fleet" ? (
                  <FleetCount />
                ) : (
                  <Sequence from={40} layout="none">
                    <NativePanel name={name} width={width} height={height} />
                  </Sequence>
                )}
              </PanelPlane>
            );
          })}
          <Img
            src={staticFile("dashboard-v4/wide-hero.png")}
            width={1600}
            height={900}
            style={{
              position: "absolute",
              borderRadius: 0,
              opacity: ease(f, 246, 253),
              transform: "translateZ(0px)",
            }}
          />
          <div
            style={{
              position: "absolute",
              left: layout.progress.x,
              top: layout.progress.y,
              transform: "translateZ(1px)",
            }}
          >
            <ProgressMotion />
          </div>
        </div>
      </AbsoluteFill>
      <div
        style={{
          position: "absolute",
          left: 122 + 650 * exit,
          top: 115 - 100 * exit,
          opacity: 1 - ease(f, 73, 99),
          transform: `scale(${1 - 0.72 * exit})`,
          transformOrigin: "0% 0%",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 13,
            fontSize: 39,
            fontWeight: 750,
          }}
        >
          <Img src={staticFile("dashboard-v2/brand-mark.svg")} width={58} />
          <span>
            Medi<span style={{ color: "#de6d20" }}>Sync</span>
          </span>
        </div>
        <div
          style={{
            marginTop: 145,
            fontSize: 124,
            fontWeight: 750,
            letterSpacing: "-.064em",
            lineHeight: 1.02,
          }}
        >
          {["ONE PLATFORM.", "EVERY ROBOT. IN SYNC."].map((line, row) => (
            <div
              key={line}
              style={{ overflow: "hidden", color: row ? "#bb5216" : "#23201d" }}
            >
              {line.split(" ").map((word, i) => {
                const p = ease(f, 2 + row * 12 + i * 4, 18 + row * 12 + i * 4);
                return (
                  <span
                    key={word}
                    style={{
                      display: "inline-block",
                      marginRight: ".22em",
                      opacity: p,
                      transform: `translateY(${(1 - p) * 95}px) rotateX(${(1 - p) * 28}deg)`,
                    }}
                  >
                    {word}
                  </span>
                );
              })}
            </div>
          ))}
        </div>
        <div
          style={{
            marginTop: 32,
            width: 104 * ease(f, 34, 53),
            height: 4,
            background: "#d9702c",
          }}
        />
      </div>
      {cue && (
        <div
          style={{
            position: "absolute",
            bottom: 18,
            left: 0,
            right: 0,
            textAlign: "center",
            fontSize: 33,
            lineHeight: 1.35,
          }}
        >
          <span
            style={{
              display: "inline-block",
              color: "#fff",
              background: "#241e19",
              padding: "7px 19px",
              borderRadius: 6,
            }}
          >
            {cue.text}
          </span>
        </div>
      )}
    </AbsoluteFill>
  );
};
