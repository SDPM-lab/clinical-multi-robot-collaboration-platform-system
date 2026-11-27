import { AbsoluteFill, Audio, Easing, Img, OffthreadVideo, interpolate, staticFile, useCurrentFrame } from "remotion";
import { Cursor } from "./RobotStatusPhaseV2";
import { WorkspaceRobot } from "./RobotStatusPhaseV9";
import capture from "./robot-status-phase-v10-capture.json";
import captions from "./robot-status-phase-v10-captions.json";

const asset = (name: string) => staticFile(`robot-status-phase-v10/${name}`);
const frameSize = { width: 1920, height: 1080 };
const pageHeight = 984;
const uiScale = 1.2;
const focus = { x: 0, y: -138, scale: 1.64 };
const mapAnchor = { x: 610, y: 519 };
const listAnchor = { x: 389, y: 381 };
const handoffEnd = 40;
const wideAt = 177;
const { c01, m01 } = capture.timing;
const motion = (f: number, from: number, to: number, easing = Easing.inOut(Easing.cubic)) =>
  interpolate(f,[from,to],[0,1],{easing,extrapolateLeft:"clamp",extrapolateRight:"clamp"});
const mix = (a: number,b: number,t: number) => a+(b-a)*t;
const rowPoint = (index: number) => {
  const {x,y,width,height}=capture.targets[index];
  return {x:(x+width*.5)*uiScale,y:(y+height*.60-capture.distance)*uiScale};
};

export const RobotStatusPhaseV10 = () => {
  const f = useCurrentFrame();
  const mapMotion = motion(f,5,37,Easing.bezier(.35,0,.45,1));
  const mapScale = mix(1,1.12,mapMotion);
  const mapX = mix(mapAnchor.x,listAnchor.x,mapMotion)-mapAnchor.x*mapScale;
  const mapY = mix(mapAnchor.y,listAnchor.y,mapMotion)-mapAnchor.y*mapScale;

  const reveal = motion(f,22,handoffEnd,Easing.bezier(.36,0,.32,1));
  const edge = mix(-138,frameSize.width,reveal);
  const pullback = motion(f,m01+1,wideAt,Easing.bezier(.42,0,.21,1));
  const scale = mix(focus.scale,1,pullback);
  const x = focus.x*(1-pullback);
  const y = focus.y*(1-pullback);

  const first=rowPoint(0), final=rowPoint(1);
  const enter=motion(f,42,57);
  const approach=motion(f,91,98);
  const change=motion(f,110,123);
  const mouse={
    x:mix(mix(470,298,enter),first.x,approach)+(final.x-first.x)*change,
    y:mix(mix(300,312,enter),first.y,approach)+(final.y-first.y)*change,
  };
  const pressed=[c01,m01].reduce((value, at)=>
    Math.max(value,motion(f,at-2,at)*(1-motion(f,at,at+4))),0);
  const orbit = motion(f,m01,145)*(1-motion(f,145,172))*60;
  const subtitle = captions.find(c=>f>=c.from&&f<c.to);

  return <AbsoluteFill style={{background:"#f4f1ec",overflow:"hidden",fontFamily:"Inter, Arial, 'Noto Sans CJK TC', sans-serif"}}>
    {f<handoffEnd&&<Img src={staticFile("robot-status-phase-v9/phase4-final.png")} style={{
      position:"absolute",...frameSize,transformOrigin:"top left",transform:`translate(${mapX}px,${mapY}px) scale(${mapScale})`,
    }}/>}
    <AbsoluteFill style={{maskImage:f<handoffEnd?
      `linear-gradient(90deg, black ${edge}px, transparent ${edge+138}px)`:undefined}}>
      <div style={{
        position:"absolute",width:frameSize.width,height:pageHeight,left:x,top:y,
        transformOrigin:"top left",transform:`scale(${scale})`,
      }}>
        <OffthreadVideo muted src={asset("workspace.mp4")} style={{width:frameSize.width,height:pageHeight}}/>
        <WorkspaceRobot pose={132+orbit}/>
      </div>
    </AbsoluteFill>
    {f>=42&&f<151&&<Cursor x={x+mouse.x*scale} y={y+mouse.y*scale} press={pressed}
      opacity={motion(f,42,47)*(1-motion(f,142,151))}/>}
    {f>=wideAt&&<span style={{position:"absolute",right:35,bottom:31,fontSize:15,color:"#62564e",fontWeight:600}}>
      Simulated telemetry
    </span>}
    {subtitle&&<div style={{position:"absolute",bottom:22,alignSelf:"center",background:"#25211e",color:"#fff",
      borderRadius:8,padding:"7px 16px",fontSize:29,fontWeight:650}}>
      {subtitle.text}
    </div>}
    <Audio src={asset("voice.wav")}/>
    <Audio src={asset("score.wav")}/>
  </AbsoluteFill>;
};
