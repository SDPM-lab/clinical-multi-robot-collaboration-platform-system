import {
  AbsoluteFill, Audio, Easing, Img, interpolate, staticFile, useCurrentFrame,
} from "remotion";
import layout from "./dashboard-layout.json";

const assets = "dashboard-reveal/";
const ease = Easing.bezier(0.22, 0.7, 0.22, 1);
const move = (frame: number, start: number, end: number, from: number, to: number) =>
  interpolate(frame, [start, end], [from, to], {
    easing: ease, extrapolateLeft: "clamp", extrapolateRight: "clamp",
  });

export const DashboardReveal: React.FC = () => {
  const frame = useCurrentFrame();
  const separation = move(frame, 62, 115, 0, 1) * move(frame, 150, 235, 1, 0);
  const show = move(frame, 14, 64, 0, 1);
  const z = move(frame, 0, 58, 1.12, 1.44)
    + move(frame, 58, 118, 0, -.62)
    + move(frame, 150, 237, 0, .16);
  const pitch = 9 * separation;
  const yaw = -12 * separation;
  const sweep = move(frame, 112, 161, -1200, 2350);

  return (
    <AbsoluteFill style={{background: "radial-gradient(ellipse at 50% 52%, #49413b, #141210 75%)", overflow: "hidden"}}>
      <Audio src={staticFile(assets + "score.wav")} />
      <AbsoluteFill style={{perspective: 2100}}>
        <AbsoluteFill style={{
          transformStyle: "preserve-3d",
          transform: `translateX(${-30 * separation}px) scale(${z}) rotateX(${pitch}deg) rotateY(${yaw}deg)`,
          opacity: move(frame, 0, 24, .2, 1),
        }}>
          <Img src={staticFile(assets + "base.png")} style={{width: 1920, height: 1080, position: "absolute", borderRadius: 18}} />
          {layout.map(({name, x, y, width, height, dx, dy, depth}, index) => {
            const stagger = move(frame, 39 + index * 5, 76 + index * 5, 0, 1);
            return (
              <div key={name} style={{
                position: "absolute", left: x, top: y, width, height,
                opacity: show * stagger, borderRadius: 8, overflow: "hidden",
                transform: `translate3d(${dx * separation}px, ${dy * separation}px, ${depth * separation}px)`,
                boxShadow: `0 ${18 * separation}px ${50 * separation}px rgba(37, 25, 14, ${.28 * separation})`,
              }}>
                <Img src={staticFile(assets + "overview.png")} style={{
                  width: 1920, height: 1080, position: "absolute", left: -x, top: -y,
                }}/>
              </div>
            );
          })}
          <Img src={staticFile(assets + "overview.png")} style={{
            position: "absolute", width: 1920, height: 1080, borderRadius: 18,
            opacity: move(frame, 228, 245, 0, 1),
          }}/>
        </AbsoluteFill>
      </AbsoluteFill>
      <AbsoluteFill style={{
        pointerEvents: "none",
        opacity: move(frame, 112, 125, 0, .18) * move(frame, 145, 161, 1, 0),
        background: `linear-gradient(111deg, transparent ${sweep - 215}px, #ffc381 ${sweep}px, transparent ${sweep + 215}px)`,
      }}/>
    </AbsoluteFill>
  );
};
