import { Easing, Img, interpolate, staticFile } from "remotion";
import { Cursor } from "./RobotStatusPhaseV2";

const robots = [
  ["C01", "Busy", "Ward B", 77],
  ["C02", "Idle", "Waiting B", 69],
  ["M01", "Idle", "Ward A", 82],
  ["M02", "Busy", "Laboratory", 91],
  ["W01", "Charging", "Charging Station A", 58],
  ["W02", "Charging", "Charging Station A", 48],
  ["W03", "Charging", "Charging Station B", 65],
] as const;
const columns = "100px 145px 290px 240px 355px 1fr";
const x=192, y=174, width=1536, header=120, row=124, windowHeight=600;
const selectedFrame=186;
const perspective=3200;
const camera={x:960,y:540};
const pivot={x:x+width/2,y:y+(header+windowHeight)/2};

function project(localX:number,localY:number,glideX:number,angle:number) {
  const radians=angle*Math.PI/180;
  const dx=x+localX+glideX-pivot.x;
  const worldX=pivot.x+Math.cos(radians)*dx;
  const depth=-Math.sin(radians)*dx;
  const scale=perspective/(perspective-depth);
  return {x:camera.x+(worldX-camera.x)*scale,y:camera.y+(y+localY-camera.y)*scale,scale};
}
const move=(f:number,a:number,b:number,easing=Easing.bezier(.33,0,.23,1)) =>
  interpolate(f,[a,b],[0,1],{easing,extrapolateLeft:"clamp",extrapolateRight:"clamp"});

export function RobotFleetCanvasV13({frame:f}:{frame:number}) {
  const thumbnail=staticFile("robot-status-phase-v12/agibot-g1.png");
  const entrance=move(f,37,65);
  const trace=move(f,36,61);
  const rim=move(f,36,41)*(1-move(f,58,75));
  const content=move(f,46,69);
  const departure=move(f,190,213);
  const straighten=move(f,55,88);
  const angle=-22*(1-straighten);
  // The camera stays fixed while the plane glides in its local coordinate system.
  const glideX=135*(1-move(f,37,88,Easing.bezier(.30,.12,.66,1)));
  const scroll=(robots.length*row-windowHeight)*move(f,92,145,Easing.bezier(.45,0,.06,1))
    -172*move(f,151,176);
  const targetY=header+2.5*row-scroll;
  const hover=move(f,174,183);
  const pointerArrival=move(f,86,92);
  const pointer=project(780-135*pointerArrival-510*hover,
    205+196*pointerArrival+(targetY-401)*hover,glideX,angle);
  const release=move(f,187,194);
  const carry=move(f,187,196);
  const anchor=project(65,targetY,glideX,angle);
  return <>
    <div style={{position:"absolute",inset:0,opacity:1-departure}}>
      <div style={{position:"absolute",inset:0,perspective,perspectiveOrigin:"960px 540px"}}>
        <div style={{position:"absolute",left:x,top:y,width,height:header+windowHeight,
          transformOrigin:"50% 50%",transform:`rotateY(${angle}deg)`,transformStyle:"preserve-3d"}}>
          <section style={{position:"absolute",inset:0,transform:`translateX(${glideX}px)`,transformStyle:"preserve-3d"}}>
            <div style={{position:"absolute",inset:0,borderRadius:25,background:"#eee5d9",
              opacity:entrance,transform:"translateZ(-17px)",boxShadow:"0 25px 58px #48351d32"}}/>
            <div style={{position:"absolute",top:18,bottom:18,right:0,width:17,transformOrigin:"right center",
              opacity:entrance,transform:"rotateY(-90deg)",background:"#e5dbce"}}/>
            <div style={{position:"relative",height:"100%",opacity:content,borderRadius:25,background:"#f4f5f4"}}>
      <div style={{height:header,background:"#fff",borderRadius:"25px 25px 0 0",padding:"22px 30px 0",boxSizing:"border-box"}}>
        <div style={{display:"flex",alignItems:"baseline",gap:18,marginBottom:16}}>
          <strong style={{fontSize:28,letterSpacing:-.65}}>Robot Fleet</strong>
          <span style={{fontSize:17,color:"#675c54"}}>All 7 · 1F</span>
        </div>
        <div style={{display:"grid",gridTemplateColumns:columns,fontSize:16,fontWeight:700,color:"#615951"}}>
          <span/><span>Robot ID</span><span>Robot Model</span><span>Operational Status</span><span>Current Location</span><span>Battery</span>
        </div>
      </div>
      <div style={{height:windowHeight,overflow:"hidden",borderRadius:"0 0 25px 25px"}}>
        <div style={{transform:`translateY(${-scroll}px)`}}>
          {robots.map(([id,status,location,battery])=>{
            const selected=id==="M01"&&f>=selectedFrame;
            const hovered=id==="M01"&&f>=179&&f<selectedFrame;
            const color=status==="Busy"?"#bd4c20":status==="Charging"?"#896414":"#3f6653";
            return <div key={id} style={{display:"grid",gridTemplateColumns:columns,alignItems:"center",
              boxSizing:"border-box",height:row,padding:"0 30px",background:selected?"#fff0e5":hovered?"#fff7ef":"#fff",
              borderBottom:"1px solid #eeeae5",boxShadow:selected?"inset 4px 0 #dc742e":"none",
              fontSize:23}}>
              <Img src={thumbnail} style={{width:70,height:86,objectFit:"contain",opacity:selected?1-release:1}}/>
              <strong style={{fontSize:27,letterSpacing:-.5}}>{id}</strong>
              <span style={{color:"#544b44"}}>Agibot Genie G1</span>
              <span style={{color,fontWeight:660}}>{status}</span>
              <span>{location}</span>
              <div style={{fontVariantNumeric:"tabular-nums",width:108,textAlign:"right"}}>
                <strong>{battery}%</strong>
                <div style={{height:4,background:"#ece8e3",marginTop:9,borderRadius:4}}>
                  <div style={{width:`${battery}%`,height:"100%",background:selected?"#d4783d":color,borderRadius:4}}/>
                </div>
              </div>
            </div>;
          })}
        </div>
      </div>
            </div>
            {f<75&&<svg width={width} height={header+windowHeight} style={{position:"absolute",inset:0,overflow:"visible",opacity:rim}}>
              <rect x={1.5} y={1.5} width={width-3} height={header+windowHeight-3} rx={23} pathLength={1}
                fill="none" stroke="#e97833" strokeWidth={3} strokeDasharray=".28 1.1"
                strokeDashoffset={.28-1.28*trace} strokeLinecap="round"/>
            </svg>}
          </section>
        </div>
      </div>
    </div>
    {f>=86&&f<193&&<Cursor x={pointer.x} y={pointer.y}
      press={move(f,184,186)*(1-move(f,186,190))} opacity={move(f,86,92)*(1-move(f,188,193))}/>}
    {f>=188&&f<198&&<Img src={thumbnail} style={{position:"absolute",
      left:anchor.x+(586-anchor.x)*carry-(35+58*carry)*anchor.scale,
      top:anchor.y+(553-anchor.y)*carry-(43+93*carry)*anchor.scale,
      width:(70+116*carry)*anchor.scale,height:(86+186*carry)*anchor.scale,objectFit:"contain",
      opacity:move(f,187,191)*(1-move(f,193,197))}}/>}
  </>;
}
