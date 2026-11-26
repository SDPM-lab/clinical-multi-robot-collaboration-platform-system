import { AbsoluteFill, Audio, cancelRender, Easing, Img, OffthreadVideo, interpolate, staticFile, useCurrentFrame, useDelayRender } from "remotion";
import { useEffect, useLayoutEffect, useRef } from "react";
import { Cursor } from "./RobotStatusPhaseV2";
import capture from "./robot-status-phase-v9-capture.json";
import { createRobotStatusScene } from "./robotStatusScene";
import { viewport } from "./robot-status-phase-v2-capture.json";
import captions from "./robot-status-phase-v9-captions.json";

const asset = (name: string) => staticFile(`robot-status-phase-v9/${name}`);
const scale = 1.2;
const pageHeight = 984;
const eased = (frame: number, from: number, to: number, easing = Easing.inOut(Easing.cubic)) =>
  interpolate(frame, [from, to], [0, 1], { easing, extrapolateLeft: "clamp", extrapolateRight: "clamp" });
const navClick = 26;
const wipeEnd = 41;
const point = (box: {x:number; y:number; width:number; height:number}, scroll = 0) =>
  [(box.x + box.width * .5) * scale, (box.y + box.height * .52 - scroll) * scale] as const;

export const WorkspaceRobot = ({ pose }: { pose: number }) => {
  const canvas = useRef<HTMLCanvasElement>(null);
  const scene = useRef<Awaited<ReturnType<typeof createRobotStatusScene>> | null>(null);
  const latest = useRef(pose);
  const { delayRender, continueRender } = useDelayRender();
  useLayoutEffect(() => {
    latest.current = pose;
    scene.current?.draw(pose);
  }, [pose]);
  useEffect(() => {
    const handle = delayRender("Loading MediSync's original Agibot model");
    let active = true;
    createRobotStatusScene(canvas.current!, staticFile("ppo-spatial/AGIBOT_A2D.glb"), 1, 1, false, true)
      .then(renderer => {
        if (!active) {
          renderer.dispose();
          return;
        }
        scene.current = renderer;
        renderer.draw(latest.current);
        continueRender(handle);
      })
      .catch(error => { if (active) cancelRender(error); });
    return () => {
      active = false;
      scene.current?.dispose();
      scene.current = null;
      continueRender(handle);
    };
  }, [delayRender, continueRender]);
  return <canvas ref={canvas} style={{
    position:"absolute",left:viewport.x * scale,top:viewport.y * scale,
    width:viewport.width * scale,height:viewport.height * scale,
  }} />;
};

export const RobotStatusPhaseV9 = () => {
  const frame = useCurrentFrame();
  const navigation = point(capture.navbar.status);
  const c01 = point(capture.targets[0]);
  const m01 = point(capture.targets[1], capture.maxScroll);
  const approach = eased(frame, 6, 23);
  const toList = eased(frame, 39, 54);
  const toM01 = eased(frame, 118, 126);
  const orbit = eased(frame,65,74) * (1 - eased(frame,74,85)) * 28
    + eased(frame,133,143) * (1 - eased(frame,143,155)) * 62;
  const wipe = eased(frame, navClick, wipeEnd);
  const navHeight = Math.max(96, Math.round(capture.navbar.navBottom * scale));
  const subtitle = captions.find(({from,to}) => frame >= from && frame < to);
  const click = [navClick, 65, 133].reduce((value, at) =>
    Math.max(value, eased(frame, at - 2, at) * (1 - eased(frame, at, at + 4))), 0);
  const cursor = navigation.map((coordinate, axis) =>
    interpolate(approach, [0,1], [axis === 0 ? 1465 : 161, coordinate])
    + (c01[axis]-coordinate)*toList + (m01[axis]-c01[axis])*toM01);

  return <AbsoluteFill style={{ background: "#f4f1ec", overflow: "hidden", fontFamily: "Inter, Arial, 'Noto Sans CJK TC', sans-serif" }}>
    {frame < wipeEnd && <Img src={asset("phase4-final.png")} style={{ width: 1920, height: 1080 }} />}
    <AbsoluteFill style={{ clipPath: frame < wipeEnd ? `inset(${navHeight}px 0 ${(1080 - navHeight) * (1 - wipe)}px 0)` : undefined }}>
      <OffthreadVideo muted src={asset("workspace.mp4")} style={{ width: 1920, height: pageHeight }} />
      <WorkspaceRobot pose={132 + orbit} />
    </AbsoluteFill>
    {frame < wipeEnd && <div style={{ position:"absolute", inset:"0 0 auto", height:navHeight, overflow:"hidden", clipPath:`inset(0 0 0 ${(1 - eased(frame,1,10)) * 100}%)` }}>
      <Img src={asset(frame < navClick ? "map-navbar.png" : "native-page.png")} style={{width:1920,height:pageHeight}} />
    </div>}
    {frame > 4 && frame < 154 && <Cursor x={cursor[0]} y={cursor[1]} press={click} opacity={eased(frame,4,9)*(1-eased(frame,147,154))}/>}
    {frame >= wipeEnd && <span style={{position:"absolute",right:35,bottom:31,fontSize:15,color:"#62564e",fontWeight:600}}>Simulated telemetry</span>}
    {subtitle && <div style={{position:"absolute",bottom:22,alignSelf:"center",background:"#25211e",color:"#fff",borderRadius:8,padding:"7px 16px",fontSize:29,fontWeight:650}}>{subtitle.text}</div>}
    <Audio src={asset("voice.wav")} />
    <Audio src={asset("score.wav")} />
  </AbsoluteFill>;
};
