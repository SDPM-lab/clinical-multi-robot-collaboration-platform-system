import {AbsoluteFill, Audio, Easing, Img, interpolate, staticFile, useCurrentFrame} from "remotion";
import type {CSSProperties} from "react";
import layout from "./dashboard-v2-layout.json";
import captions from "./dashboard-v2-captions.json";

const asset = (file: string) => staticFile(`dashboard-v2/${file}`);
const out = Easing.bezier(.2, .8, .3, 1);
const inOut = Easing.bezier(.45, 0, .2, 1);
const tween = (f: number, from: number, to: number, a = 0, b = 1, easing = out) =>
  interpolate(f, [from, to], [a, b], {easing, extrapolateLeft: "clamp", extrapolateRight: "clamp"});

type Box = {x: number; y: number; width: number; height: number};
const viewport = {width: 1600, height: 900};
const panel = (box: Box): CSSProperties => ({
  position: "absolute", left: box.x, top: box.y, width: box.width, height: box.height,
});

const Phrase = ({words, from, color}: {words: string[]; from: number; color: string}) => {
  const frame = useCurrentFrame();
  return (
    <div style={{display: "flex", gap: ".22em", color, overflow: "hidden", paddingBottom: ".095em"}}>
      {words.map((word, index) => {
        const p = tween(frame, from + index * 4, from + index * 4 + 19);
        return <span key={word} style={{
          display: "block", opacity: p, filter: `blur(${(1 - p) * 8}px)`,
          transform: `translateY(${(1 - p) * 65}%) rotateX(${(1 - p) * -34}deg)`,
          transformOrigin: "50% 100%",
        }}>{word}</span>;
      })}
    </div>
  );
};

const ProductPanel = ({box, start, mode}: {box: Box; start: number; mode?: "chart" | "gauge"}) => {
  const f = useCurrentFrame();
  const unfold = tween(f, start, start + 24);
  const settle = tween(f, 222, 250, 0, 1, inOut);
  const lift = unfold * (1 - settle);
  const mask = mode === "chart"
    ? `inset(${72 * (1 - unfold)}% 0 0 0)`
    : `inset(0 0 ${100 * (1 - unfold)}% 0)`;
  return <>
    <div style={{
      ...panel(box), opacity: (1 - settle) * (1 - .42 * unfold), borderRadius: 9,
      background: "linear-gradient(180deg, #f8f6f200 0px, #f8f6f2c7 54px, #f8f6f2de 100%)",
    }} />
    <div style={{
      ...panel(box), transform: `translate3d(${lift * 2}px,${-14 * lift}px,${lift * 24}px)`,
      borderRadius: 9, overflow: "hidden", opacity: unfold,
      boxShadow: `0 ${10 * lift}px ${25 * lift}px rgba(42,31,21,${.18 * lift})`,
      clipPath: mask,
    }}>
      <Img src={asset("overview.png")} style={{
        ...viewport, position: "absolute", left: -box.x, top: -box.y, maxWidth: "none",
      }} />
      {mode === "gauge" && f < 180 && <div style={{
        position: "absolute", left: 160 - box.x, top: 273 - box.y,
        width: 58, height: 38, display: "grid", placeItems: "center",
        background: "linear-gradient(#fff3c8, #fff2c3)", color: "#38352b",
        fontSize: 43, fontWeight: 500, lineHeight: "38px",
        fontVariantNumeric: "tabular-nums",
      }}>{Math.round(tween(f, 151, 178, 0, 75))}</div>}
    </div>
  </>;
};

export const DashboardRevealV2 = () => {
  const f = useCurrentFrame();
  const retreat = tween(f, 59, 148, 0, 1, inOut);
  const hero = tween(f, 226, 267, 0, 1, inOut);
  const headlineFade = 1 - tween(f, 65, 91);
  const headlineDock = tween(f, 55, 88, 0, 1, inOut);
  const titleY = -270 * headlineDock;
  const subtitle = captions.find(cue => f >= cue.start && f < cue.end);
  const audienceFocus = tween(f, 254, 274) * (1 - tween(f, 287, 299, 0, .55));
  const dock = tween(f, 76, 130);

  return (
    <AbsoluteFill style={{
      background: "radial-gradient(ellipse at 71% 60%, #fff 0%, #faf9f6 62%, #f4f0eb 100%)",
      fontFamily: "Arial, Helvetica, sans-serif", color: "#201d1a", overflow: "hidden",
    }}>
      <Audio src={asset("voice.wav")} volume={.82} />
      <Audio src={asset("sound.wav")} volume={.74} />
      <AbsoluteFill style={{perspective: 2200, opacity: tween(f, 63, 94)}}>
        <div style={{
          position: "absolute", left: 160, top: 75, ...viewport,
          transform: `translate3d(${153 * (1 - retreat)}px,${414 * (1 - retreat) - 9 * hero}px,0)
            scale(${.84 + .292 * retreat - .016 * hero}) rotateX(${13 * (1 - retreat)}deg)
            rotateY(${-15 * (1 - retreat)}deg)`,
          transformStyle: "preserve-3d",
          borderRadius: 20,
          boxShadow: "0 26px 75px #30271d24, 0 0 0 1px #a89a8a30",
        }}>
          <Img src={asset("overview.png")} style={{...viewport, borderRadius: 20}} />
          <ProductPanel box={layout.complete} start={150} mode="gauge" />
          <ProductPanel box={layout.schedule} start={165} />
          <ProductPanel box={layout.fleet} start={179} />
          <ProductPanel box={layout.battery} start={193} mode="chart" />
          <div style={{
            position: "absolute", left: layout.dispatch.x + 4, top: layout.dispatch.y + layout.dispatch.height + 3,
            width: Math.max(20, layout.dispatch.width - 8) * audienceFocus, height: 2,
            borderRadius: 2, background: "#e9741f",
          }}/>
        </div>
      </AbsoluteFill>
      <div style={{
        position: "absolute", left: 132, top: 143, display: "flex", alignItems: "center", gap: 13,
        opacity: tween(f, 0, 14) * headlineFade, transform: `translateY(${titleY}px)`,
        fontWeight: 750, fontSize: 39, letterSpacing: "-.035em",
      }}>
        <Img src={asset("brand-mark.svg")} style={{width: 64}} />
        <span>Medi<span style={{color: "#e77111"}}>Sync</span></span>
      </div>
      <div style={{
        position: "absolute", left: 126, top: 346, color: "#1b1917",
        fontSize: 133, fontWeight: 800, letterSpacing: "-.063em", lineHeight: .98,
        opacity: headlineFade, transformOrigin: "left top",
        transform: `translateY(${titleY}px) scale(${1 - .75 * headlineDock})`,
      }}>
        <Phrase words={["ONE", "PLATFORM."]} from={4} color="#22201e" />
        <Phrase words={["EVERY", "ROBOT.", "IN", "SYNC."]} from={20} color="#c95b10" />
        <div style={{marginTop: 28, height: 5, width: 116 * tween(f, 40, 54), background: "#ee812e"}} />
      </div>
      <div style={{
        position: "absolute", left: 130 + 610 * dock, top: 711 - 684 * dock,
        width: 116 * (1 - .68 * dock), height: 3, background: "#ed812f",
        opacity: tween(f, 59, 70) * (1 - tween(f, 122, 139)),
      }}/>
      <div style={{
        position: "absolute", bottom: 24, right: 66, color: "#51463b", fontSize: 17,
        opacity: tween(f, 119, 147),
      }}>Simulated Data</div>
      {subtitle && <div style={{
        position: "absolute", bottom: 30, left: 360, right: 360, textAlign: "center", fontSize: 30,
      }}>
        <span style={{
          color: "#fff", background: "#251f1a", borderRadius: 6, padding: "8px 16px", display: "inline-block",
        }}>{subtitle.text}</span>
      </div>}
    </AbsoluteFill>
  );
};
