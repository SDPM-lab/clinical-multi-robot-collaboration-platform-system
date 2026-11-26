import {AbsoluteFill,Audio,Img,staticFile,useCurrentFrame} from "remotion";
import {Cursor,Robot} from "./RobotStatusPhaseV2";
import {Battery,Temperature} from "./RobotStatusPhaseV7";
import geometry from "./robot-status-phase-v2-capture.json";
import fleet from "./live-map-phase-v3-1-capture.json";
import captions from "./robot-status-phase-v8-captions.json";

const paper="#faf7f3", ink="#26211e", orange="#bc4d1d";
const native=(file:string)=>staticFile("robot-status-phase-v2/"+file+".png");
const asset=(file:string)=>staticFile("robot-status-phase-v8/"+file);
const unit=(f:number,a:number,b:number)=>Math.min(1,Math.max(0,(f-a)/(b-a)));
const ease=(f:number,a:number,b:number)=>{const t=unit(f,a,b);return t*t*(3-2*t);};
const mix=(a:number,b:number,t:number)=>a+(b-a)*t;
const {list,m01,maxScroll,viewport}=geometry;
const point=fleet.frames[fleet.frames.length-1].fleet[2].point;
const anchor={x:78+point[0]*.917-145,y:194+(point[1]-108)*.917-40};
const select=143;
const columns=[
  {name:"Battery",fill:"#edf8f1",start:216,end:241,origin:1718},
  {name:"Temperature",fill:"#fff7f3",start:226,end:250,origin:1502},
  {name:"Robot information",fill:"#fff1ca",start:243,end:261,origin:1455},
];

export const RobotStatusPhaseV8=()=>{
  const f=useCurrentFrame();
  const state=f<select?"c01":"m01";
  const iris=ease(f,10,52);
  const focus=ease(f,57,76);
  const s=mix(1.05,1.28,focus), px=mix(120,76,focus), py=mix(117,-40,focus);
  const scrolling=unit(f,74,109);
  const scroll=maxScroll*(1-(1-scrolling)**3);
  const reveal=ease(f,150,168);
  const heroOut=ease(f,207,224);
  const x=px+(m01.x+m01.width*.62)*s, y=py+(m01.y+m01.height*.52-scroll)*s;
  const mouse=ease(f,60,74), aim=ease(f,115,139);
  const subtitle=captions.find(c=>f>=c.from&&f<c.to);
  const title=f<150?"EXPLORE YOUR ROBOT FLEET.":f<220?"YOUR ROBOT. IN FOCUS.":"ROBOT STATUS AT A GLANCE.";
  const clip=f<52?`ellipse(${2370*iris}px ${1550*iris}px at ${anchor.x}px ${anchor.y}px)`:undefined;
  return <AbsoluteFill style={{background:paper,color:ink,overflow:"hidden",fontFamily:"Inter,Arial,'Noto Sans CJK TC',sans-serif"}}>
    {f<52&&<Img src={staticFile("robot-status-phase-v1/live-map.png")} style={{width:1920,height:1080}}/>}
    <AbsoluteFill style={{background:paper,clipPath:clip}}>
      <div style={{position:"absolute",left:110,top:34,display:"flex",gap:10,alignItems:"center",fontSize:27,fontWeight:800}}>
        <Img src={staticFile("dashboard-v2/brand-mark.svg")} style={{width:41,height:29}}/><span>Medi<span style={{color:orange}}>Sync</span></span>
      </div>
      <div style={{position:"absolute",left:110,top:85,fontSize:43,fontWeight:850,letterSpacing:-1.2}}>{title}</div>
      {f<169&&<div style={{position:"absolute",left:0,right:0,top:143,bottom:90,overflow:"hidden",opacity:1-reveal}}>
        <div style={{position:"absolute",left:px,top:py-143,width:1600,height:820,
          transform:`scale(${s})`,transformOrigin:"top left",overflow:"hidden",borderRadius:13}}>
          <Img src={native(state)} style={{position:"absolute",inset:0,width:1600,height:820}}/>
          <div style={{position:"absolute",left:list.x,top:list.y,width:list.width,height:list.height,overflow:"hidden"}}>
            <Img src={asset(state+"-list.png")} style={{position:"absolute",left:0,top:-scroll,width:list.width,
              height:list.height+maxScroll}}/>
          </div>
          <div style={{position:"absolute",left:m01.x,top:m01.y-scroll,width:m01.width,height:m01.height,
            borderRadius:10,background:"#e8783918",opacity:ease(f,134,141)*(1-ease(f,142,144))}}/>
        </div>
      </div>}
      {f>=147&&f<225&&<div style={{position:"absolute",left:mix(px+viewport.x*s,300,reveal),top:mix(py+viewport.y*s,148,reveal),
        width:mix(viewport.width*s,1320,reveal),height:mix(viewport.height*s,797,reveal),opacity:reveal*(1-heroOut)}}>
        <Robot f={mix(132,198,ease(f,151,198))} showcase/>
      </div>}
      {f>=220&&<div style={{position:"absolute",right:112,top:44,fontSize:16,fontWeight:650,color:"#65554d"}}>M01 · Demo Telemetry</div>}
      {columns.map((c,i)=>{
        if(f<=c.start)return null;
        const t=ease(f,c.start,c.end);
        const left=112+i*574;
        return <section key={c.name} style={{position:"absolute",left:mix(c.origin,left+276,t)-276,
          top:mix(310+i*28,234,t),width:552,height:578,boxSizing:"border-box",padding:34,
          borderRadius:22,background:c.fill,border:"1px solid #e6d9ce",overflow:"hidden",opacity:t,
          transform:`scale(${mix(.48,1,t)})`,
          clipPath:i===0?`inset(0 ${100*(1-t)}% 0 0 round 22px)`:i===1?`inset(0 ${50*(1-t)}% 0 round 22px)`:
            `inset(0 0 ${100*(1-t)}% 0 round 22px)`}}>
          <h2 style={{fontSize:31,margin:0,fontWeight:760}}>{c.name}</h2>
          {i<2?<div style={{position:"absolute",left:"50%",top:"53%",transform:"translate(-50%,-50%) scale(2.05)"}}>
            {i===0?<Battery f={mix(184,211,ease(f,231,263))}/>:<Temperature f={mix(193,218,ease(f,237,269))}/>}
          </div>:<dl style={{margin:"22px 0 0",display:"grid",gap:0}}>
            {[["Robot ID","M01"],["Operational status","Idle"],["Connection","Connected"],
              ["Current location","Ward A"],["Robot model","Agibot Genie G1"]].map(([key,value],j)=>
              <div key={key} style={{borderTop:"1px solid #dbcba2",padding:"13px 0",opacity:ease(f,244+j*3,254+j*3)}}>
                <dt style={{fontSize:17,color:"#68594b"}}>{key}</dt>
                <dd style={{margin:"2px 0 0",fontSize:25,fontWeight:730}}>{value}</dd>
              </div>)}
          </dl>}
        </section>;
      })}
      {f>=60&&f<152&&<Cursor x={mix(mix(635,473,mouse),x,aim)} y={mix(mix(389,475,mouse),y,aim)}
        press={ease(f,141,143)*(1-ease(f,143,147))} opacity={ease(f,60,66)*(1-ease(f,147,152))}/>}
    </AbsoluteFill>
    {subtitle&&<div style={{position:"absolute",bottom:24,alignSelf:"center",background:"#231e1bea",color:"white",
      borderRadius:8,padding:"6px 18px",fontSize:29,fontWeight:650}}>{subtitle.text}</div>}
    <Audio src={asset("voice.wav")}/><Audio src={asset("score.wav")}/>
  </AbsoluteFill>;
};
