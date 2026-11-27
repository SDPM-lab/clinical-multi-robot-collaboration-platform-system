import {AbsoluteFill, Audio, Easing, OffthreadVideo, interpolate, staticFile, useCurrentFrame} from "remotion";
import captions from "./live-map-tracking-captions.json";
import capture from "./live-map-tracking-capture.json";

const accent="#e85d24";
const fade=(f:number,a:number,b:number)=>interpolate(f,[a,b],[0,1],{
  extrapolateLeft:"clamp",extrapolateRight:"clamp",easing:Easing.out(Easing.cubic)
});
const mix=(a:number,b:number,p:number)=>a+(b-a)*p;

function Point({position,label,kind,opacity}: {position:number[];label:string;kind:string;opacity:number}) {
  const x=Math.max(155,Math.min(1710,position[0]*1.5));
  const y=Math.max(190,Math.min(880,position[1]*1.5));
  return <div style={{position:"absolute",left:x,top:y,opacity,transform:"translate(-50%,-100%)",
    display:"grid",justifyItems:"center",pointerEvents:"none"}}>
    <div style={{padding:"10px 16px",whiteSpace:"nowrap",background:"#fffaf7",color:"#211b18",borderRadius:11,
      boxShadow:"0 3px 16px #1f1c1829",border:"1px solid #f4d8ca",fontSize:24,fontWeight:750}}>
      <span style={{color:accent,fontSize:15,fontWeight:850,letterSpacing:1,marginRight:9}}>{kind}</span>{label}
    </div>
    <div style={{height:19,width:2,background:accent}}/>
    <div style={{height:10,width:10,borderRadius:8,background:accent,border:"2px solid white"}}/>
  </div>;
}
export const LiveMapTrackingPrototype=()=>{
  const frame=useCurrentFrame();
  const sample=capture.frames[frame];
  const caption=captions.find(({from,to})=>frame>=from&&frame<to);
  const route=fade(frame,60,71)*(1-fade(frame,146,161));
  const tracking=fade(frame,155,178)*(1-fade(frame,254,281));
  const monitoring=fade(frame,278,297)*(1-fade(frame,355,375));
  const finish=fade(frame,362,390);
  const progress=sample.progress;
  const idX=mix(Math.max(230,Math.min(1610,sample.robot[0]*1.5)),1500,finish);
  const idY=mix(Math.max(177,Math.min(881,sample.robot[1]*1.5)),680,finish);
  return <AbsoluteFill style={{background:"#eae7e4",fontFamily:"Inter, Arial, Noto Sans CJK TC, sans-serif",color:"#211b18"}}>
    <OffthreadVideo src={staticFile("live-map-tracking/map-plates.mp4")} muted
      style={{width:"100%",height:"100%",objectFit:"cover"}}/>
    <div style={{position:"absolute",right:87,bottom:96,padding:"9px 15px",borderRadius:8,
      background:"#fffaf5ed",border:"1px solid #e7d9ce",fontSize:20,fontWeight:700}}>
      {frame<60?"Simulated task":frame<150?"Reference route · Simulated task":frame<270?"Simulated third-person camera":"Simulated execution"}
    </div>
    <Point position={sample.source} label="Pharmacy" kind="SOURCE" opacity={route}/>
    <Point position={sample.destination} label="Ward A" kind="DESTINATION" opacity={route*fade(frame,72,84)}/>
    {frame<59&&<Point position={sample.robot} label="M01" kind="ROBOT" opacity={fade(frame,16,27)*(1-fade(frame,53,59))}/>}
    <div style={{position:"absolute",right:94,top:138,opacity:tracking,padding:"13px 18px",
      background:"#fffaf7eb",border:"1px solid #eed5c7",borderRadius:10,fontSize:23}}>
      <b style={{color:accent}}>Following M01</b> · Third person
    </div>
    <div style={{position:"absolute",right:75,bottom:156,width:330,opacity:monitoring,background:"#fffaf5f2",
      border:"1px solid #e9d7ca",borderRadius:16,padding:"24px 26px",boxShadow:"0 4px 18px #211b181a"}}>
      <div style={{fontSize:19,color:accent,fontWeight:800}}>T0002 · M01</div>
      <div style={{fontSize:28,fontWeight:750,margin:"8px 0 18px"}}>Task progress</div>
      <div style={{fontSize:17,color:"#71665d"}}>Global view · Follow off</div>
      {["Source · Pharmacy","En route","Destination · Ward A"].map((name,i)=><div key={name} style={{
        fontSize:20,display:"flex",alignItems:"center",gap:12,marginTop:13,
        color:[true,progress>0,progress>=1][i]?"#211b18":"#71665d"}}>
        <span style={{width:9,height:9,borderRadius:8,background:[true,progress>0,progress>=1][i]?accent:"#d5c8bf"}}/>{name}
      </div>)}
    </div>
    <div style={{position:"absolute",left:idX,top:idY,opacity:fade(frame,280,299),transform:"translate(-50%,-100%)",
      background:"#fffaf9f2",boxShadow:"0 3px 18px #221b1833",border:"1px solid #e3bbab",borderRadius:14,
      padding:mix(12,23,finish),minWidth:mix(0,220,finish),textAlign:"center"}}>
      <span style={{color:accent,fontSize:mix(25,61,finish),fontWeight:850}}>M01</span>
      {frame>=360&&<div style={{fontSize:21,opacity:finish,fontWeight:650}}>Robot tracking · Ward A</div>}
    </div>
    {caption&&<div style={{position:"absolute",alignSelf:"center",bottom:33,padding:"9px 22px",
      borderRadius:8,background:"#211b18",color:"white",fontSize:32}}>{caption.text}</div>}
    <Audio src={staticFile("live-map-tracking/voice.wav")}/>
    <Audio src={staticFile("live-map-tracking/score.wav")}/>
  </AbsoluteFill>;
};
