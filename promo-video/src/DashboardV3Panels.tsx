import { Easing, interpolate, spring, useCurrentFrame } from "remotion";
import type { ReactNode } from "react";

export const ease = (frame: number, start: number, end: number) =>
  interpolate(frame, [start, end], [0, 1], {
    easing: Easing.bezier(0.31, 0, 0.18, 1),
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
type Plane = {
  x: number;
  y: number;
  w: number;
  h: number;
  start: number;
  dx: number;
  dy: number;
  z: number;
  rx: number;
  ry: number;
  origin: string;
  children: ReactNode;
  shadowFollowsDepth?: boolean;
  releaseShadow?: boolean;
};
export const PanelPlane = ({
  x,
  y,
  w,
  h,
  start,
  dx,
  dy,
  z,
  rx,
  ry,
  origin,
  children,
  shadowFollowsDepth = false,
  releaseShadow = false,
}: Plane) => {
  const f = useCurrentFrame();
  const duration = 43;
  const local = Math.max(0, f - start);
  const springProgress = spring({
    frame: local,
    fps: 30,
    durationInFrames: duration,
    config: { damping: 22, stiffness: 105, mass: 0.84 },
  });
  const distance = f >= start + duration ? 0 : 1 - springProgress;
  const shadowStrength = ease(f, start, start + 12);
  const blur = 0.9 * (1 - ease(f, start, start + 17)) * shadowStrength;
  const left = x + dx * distance,
    top = y + dy * distance;
  return (
    <>
      <div
        style={{
          position: "absolute",
          left: left + 13 * distance,
          top: top + 12 + 15 * distance,
          width: w,
          height: h,
          transform: shadowFollowsDepth
            ? `translateZ(${Math.min(-8, z * distance - 9)}px)`
            : "translateZ(-8px)",
          borderRadius: 13,
          opacity:
            shadowStrength *
            (shadowFollowsDepth ? 0.64 : 1) *
            (releaseShadow ? 1 - ease(f, start + 34, start + duration) : 1) *
            (0.12 + 0.16 * (1 - Math.abs(distance))),
          background: "#8a7561",
          filter: `blur(${8 + 19 * Math.abs(distance)}px)`,
        }}
      />
      <section
        style={{
          position: "absolute",
          left: x,
          top: y,
          width: w,
          height: h,
          boxSizing: "border-box",
          overflow: "hidden",
          opacity: shadowStrength,
          borderRadius: 13,
          transformOrigin: origin,
          transform: `translate3d(${dx * distance}px,${dy * distance}px,${z * distance}px) rotateX(${rx * distance}deg) rotateY(${ry * distance}deg)`,
          color: "#24221f",
          filter: `blur(${blur}px)`,
        }}
      >
        {children}
      </section>
    </>
  );
};
