import {AbsoluteFill, Img, staticFile, useCurrentFrame} from "remotion";
import {ScheduleStoryboard, wideStage} from "./TaskCreationV6Schedule";

const accent="#ea7839";
const ink="#261e19";

const HeroForm = ({selected, progress=selected?1:0, sheen=0, pressed=0, loading=false}: {selected:boolean;progress?:number;sheen?:number;pressed?:number;loading?:boolean}) =>
  <div style={{position:"absolute",left:1010,top:74,width:612,height:912,borderRadius:24,
    border:"1px solid #edc5ae",overflow:"hidden",background:"#fafafa",
    boxShadow:"0 42px 94px #77472d24, 0 8px 18px #80402117"}}>
    <div style={{position:"absolute",left:-24*1.47,top:-100*1.47,width:1600,height:900,
      transform:"scale(1.47)",transformOrigin:"0 0"}}>
      <Img src={staticFile("task-creation-v6/route.png")} style={{width:1600,height:900}} />
      <div style={{position:"absolute",left:39,top:216,width:385,height:31,boxSizing:"border-box",
        border:"1px solid #e8a988",boxShadow:"0 0 0 2px #fdebdf",borderRadius:6}} />
      <div style={{position:"absolute",left:39,top:287,width:188,height:31,boxSizing:"border-box",
        border:"1px solid #eac8b6",borderRadius:7}} />
      <div style={{position:"absolute",left:237,top:287,width:187,height:31,boxSizing:"border-box",
        border:"1px solid #eac8b6",borderRadius:7}} />
      <div style={{position:"absolute",left:39,top:500,width:386,height:28,display:"grid",
        gridTemplateColumns:"repeat(4, 1fr)",borderRadius:6,overflow:"hidden",background:"#e9e9e8",
        color:"#5f5753",fontSize:11.5,isolation:"isolate"}}>
        <div style={{position:"absolute",left:96.5*(1+progress),top:0,width:96.5,height:28,borderRadius:6,
          background:`color-mix(in srgb, #ffa372 ${progress*100}%, #ffe4d4)`,zIndex:-1}} />
        {["Low","Normal","High","Emergency"].map((label)=>{
          const active=label===(selected?"High":"Normal");
          return <div key={label} style={{display:"grid",placeItems:"center",borderRadius:6,
            color:active?ink:undefined,
            fontWeight:active?700:500}}>{label}</div>;
        })}
      </div>
      <div style={{position:"absolute",left:39,top:567,width:385,height:99,borderRadius:6,boxSizing:"border-box",
        background:selected?"#fffaf6":"#fff",border:`1px solid ${selected?"#dc976e":"#dccdc3"}`,
        padding:"9px 10px",fontSize:11.7,lineHeight:1.65,color:ink}}>
        Deliver medication from Pharmacy to Ward A.<br />
        Handle as high priority.
      </div>
      <div style={{position:"absolute",left:340,top:676,width:87,height:30,borderRadius:6,
        background:pressed? `color-mix(in srgb, #ce632d ${pressed*45}%, #f58949)` :
          selected&&sheen===0?"linear-gradient(110deg,#f58949 20%,#ffad77 47%,#f58949 75%)":"#f7945d",
        overflow:"hidden",
        color:"#291c15",fontSize:12,fontWeight:700,display:"grid",placeItems:"center"}}>
        {sheen>0&&sheen<1&&<div style={{position:"absolute",inset:0,background:"linear-gradient(110deg, transparent 26%, #ffe4c59c 50%, transparent 74%)",
          transform:`translateX(${-100+200*sheen}%)`,pointerEvents:"none"}} />}
        <span style={{position:"relative"}}>{loading?"Creating…":"Create task"}</span>
      </div>
    </div>
  </div>;

export const HeroKeyframe = ({selected, progress, sheen, pressed, loading, focus=1}:Parameters<typeof HeroForm>[0]&{focus?:number}) =>
  <AbsoluteFill style={{...wideStage,background:`radial-gradient(ellipse at 69% 49%, rgba(255,222,201,${.64*focus}), #faf7f2 53%)`}}>
    <div style={{position:"absolute",left:144,top:353,fontSize:103,fontWeight:750,letterSpacing:"-.053em",
      lineHeight:1.01,color:ink}}>
      Create with<br /><span style={{color:"#d75918"}}>confidence.</span>
    </div>
    <HeroForm selected={selected} progress={progress} sheen={sheen} pressed={pressed} loading={loading} />
  </AbsoluteFill>;

export const RescheduleDialog = ({opacity=1,pressed=0}:{opacity?:number;pressed?:number}) =>
  <AbsoluteFill style={{opacity}}>
    <AbsoluteFill style={{background:"#39281d20"}} />
    <div style={{position:"absolute",left:515,top:289,width:890,height:500,boxSizing:"border-box",
      background:"#fffdfa",border:"1px solid #ebd6ca",borderRadius:24,boxShadow:"0 24px 68px #6241282e",
      padding:"46px 52px 34px",color:ink}}>
      <div style={{fontSize:53,fontWeight:750,letterSpacing:"-.04em"}}>Reschedule task</div>
      <div style={{marginTop:9,fontSize:24,color:"#6d5346",fontWeight:600}}>T0002 · Medication delivery</div>
      <div style={{display:"flex",alignItems:"center",gap:22,marginTop:30}}>
        <div style={{padding:"13px 22px",borderRadius:10,background:"#f4eee9",fontSize:38,
          letterSpacing:"-.025em",fontWeight:720,fontVariantNumeric:"tabular-nums"}}>14:20</div>
        <div style={{fontSize:31,color:"#8a5b41"}}>→</div>
        <div style={{padding:"13px 22px",borderRadius:10,background:"#ffeadc",fontSize:38,color:"#9a4017",
          letterSpacing:"-.025em",fontWeight:760,fontVariantNumeric:"tabular-nums"}}>15:05</div>
      </div>
      <div style={{marginTop:24,fontSize:20,color:"#63554b"}}>
        This task will return to scheduling at the new time.
      </div>
      <div style={{display:"flex",justifyContent:"flex-end",gap:12,marginTop:46,fontSize:19,fontWeight:700}}>
        <div style={{padding:"14px 24px",border:"1px solid #e2d4ca",borderRadius:8,background:"#fff"}}>Cancel</div>
        <div style={{padding:"14px 24px",border:`1px solid ${accent}`,borderRadius:8,background:`color-mix(in srgb, #dd7138 ${pressed*35}%, #ffa271)`}}>Re-add task</div>
      </div>
    </div>
  </AbsoluteFill>;

export const TaskCreationV7Keyframes = () => {
  const frame=useCurrentFrame();
  return frame===2?<AbsoluteFill style={wideStage}><ScheduleStoryboard phase="B" /><RescheduleDialog /></AbsoluteFill>:<HeroKeyframe selected={frame===1} />;
};
