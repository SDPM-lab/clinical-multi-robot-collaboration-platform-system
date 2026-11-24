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
import layout from "./dashboard-v3-layout.json";

const panels = [
  {
    name: "schedule",
    start: 74,
    dx: 158,
    dy: -6,
    z: -190,
    rx: 4,
    ry: -27,
    origin: "100% 45%",
  },
  {
    name: "gauge",
    start: 92,
    dx: -96,
    dy: 0,
    z: 150,
    rx: -12,
    ry: 24,
    origin: "0% 70%",
  },
  {
    name: "network",
    start: 116,
    dx: -116,
    dy: 48,
    z: -172,
    rx: 24,
    ry: 17,
    origin: "0% 100%",
  },
  {
    name: "fleet",
    start: 128,
    dx: -121,
    dy: 78,
    z: -123,
    rx: 26,
    ry: 17,
    origin: "0% 100%",
  },
  {
    name: "battery",
    start: 144,
    dx: -20,
    dy: 153,
    z: 140,
    rx: -29,
    ry: -6,
    origin: "50% 100%",
  },
  {
    name: "progress",
    start: 157,
    dx: 136,
    dy: 106,
    z: -182,
    rx: 24,
    ry: -24,
    origin: "100% 90%",
  },
] as const;

const captions = [
  { start: 17, end: 63, text: "這是 MediSync。" },
  { start: 63, end: 157, text: "整合智慧調度、任務管理與即時監控，" },
  { start: 157, end: 247, text: "讓多機器人協作，更有效率。" },
];

export type DashboardV3Props = { voiceover?: string };

export const DashboardRevealV3 = ({ voiceover }: DashboardV3Props) => {
  const f = useCurrentFrame();
  const exit = ease(f, 49, 86);
  const camera = ease(f, 70, 234);
  const screen = ease(f, 58, 86);
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
      <Audio src={staticFile("dashboard-v3/mix.wav")} volume={0.85} />
      {voiceover && (
        <Sequence from={14} layout="none">
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
            top: 55,
            width: 1600,
            height: 900,
            transformStyle: "preserve-3d",
            transform: `translate3d(${32 * (1 - camera)}px,${65 * (1 - camera)}px,${-125 * (1 - camera)}px) rotateX(${7 * (1 - camera)}deg) rotateY(${-9 * (1 - camera)}deg) scale(1.08)`,
          }}
        >
          <Img
            src={staticFile("dashboard-v3/native-base.png")}
            width={1600}
            height={900}
            style={{
              position: "absolute",
              borderRadius: 18,
              boxShadow: "0 20px 60px #513c2433",
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
                {...motion}
              >
                <NativePanel name={name} width={width} height={height} />
              </PanelPlane>
            );
          })}
          <Img
            src={staticFile("dashboard-v3/native-overview.png")}
            width={1600}
            height={900}
            style={{
              position: "absolute",
              borderRadius: 18,
              opacity: ease(f, 227, 247),
              transform: "translateZ(1px)",
            }}
          />
          <div
            style={{
              position: "absolute",
              left: 1369,
              top: 68,
              fontSize: 12,
              color: "#574d45",
              background: "#fff9f1e8",
              borderRadius: 4,
              padding: "5px 10px",
              opacity: ease(f, 202, 234),
              transform: "translateZ(3px)",
            }}
          >
            Simulated Data
          </div>
          <div
            style={{
              position: "absolute",
              left: 620,
              top: 46,
              width: 100 * ease(f, 254, 277),
              height: 2,
              background: "#d77734",
              transform: "translateZ(3px)",
            }}
          />
        </div>
      </AbsoluteFill>
      <div
        style={{
          position: "absolute",
          left: 122 + 650 * exit,
          top: 115 - 100 * exit,
          opacity: 1 - ease(f, 62, 84),
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
            bottom: 33,
            left: 0,
            right: 0,
            textAlign: "center",
            fontSize: 37,
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
