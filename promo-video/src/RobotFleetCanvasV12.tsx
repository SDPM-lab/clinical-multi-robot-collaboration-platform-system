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
const selectedFrame=160;
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

export function RobotFleetCanvasV12({frame:f}:{frame:number}) {
  const thumbnail=staticFile("robot-status-phase-v12/agibot-g1.png");
  const entrance=move(f,31,45);
  const departure=move(f,165,185);
  const straighten=move(f,160,172);
  const angle=-57*(1-straighten);
  // The outer transform fixes the plane orientation during the glide.
  // Its child translates along the plane's own X axis before projection.
  const glideX=305-370*move(f,31,153,Easing.bezier(.30,.12,.66,1))
    +65*straighten;
  const scroll=(robots.length*row-windowHeight)*move(f,55,111,Easing.bezier(.45,0,.06,1))
    -172*move(f,116,145);
  const targetY=header+2.5*row-scroll;
  const hover=move(f,143,154);
  const pointerArrival=move(f,47,56);
  const pointer=project(780-135*pointerArrival-510*hover,
    205+196*pointerArrival+(targetY-401)*hover,glideX,angle);
  const release=move(f,162,169);
  const carry=move(f,162,171);
  const anchor=project(65,targetY,glideX,angle);
  return <>
    <div style={{position:"absolute",inset:0,opacity:entrance*(1-departure)}}>
      <div style={{position:"absolute",inset:0,perspective,perspectiveOrigin:"960px 540px"}}>
        <div style={{position:"absolute",left:x,top:y,width,height:header+windowHeight,
          transformOrigin:"50% 50%",transform:`rotateY(${angle}deg)`,transformStyle:"preserve-3d"}}>
          <section style={{position:"absolute",inset:0,transform:`translateX(${glideX}px)`,transformStyle:"preserve-3d"}}>
            <div style={{position:"absolute",inset:0,borderRadius:25,background:"#eee5d9",
              transform:"translateZ(-17px)",boxShadow:"0 25px 58px #48351d32"}}/>
            <div style={{position:"absolute",top:18,bottom:18,right:0,width:17,transformOrigin:"right center",
              transform:"rotateY(-90deg)",background:"#e5dbce"}}/>
            <div style={{position:"relative",height:"100%",borderRadius:25,background:"#f4f5f4"}}>
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
            const hovered=id==="M01"&&f>=151&&f<selectedFrame;
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
          </section>
        </div>
      </div>
    </div>
    {f>=47&&f<168&&<Cursor x={pointer.x} y={pointer.y}
      press={move(f,158,160)*(1-move(f,160,164))} opacity={move(f,47,54)*(1-move(f,162,168))}/>}
    {f>=163&&f<171&&<Img src={thumbnail} style={{position:"absolute",
      left:anchor.x+(586-anchor.x)*carry-(35+58*carry)*anchor.scale,
      top:anchor.y+(553-anchor.y)*carry-(43+93*carry)*anchor.scale,
      width:(70+116*carry)*anchor.scale,height:(86+186*carry)*anchor.scale,objectFit:"contain",
      opacity:move(f,162,166)*(1-move(f,167,170))}}/>}
  </>;
}
