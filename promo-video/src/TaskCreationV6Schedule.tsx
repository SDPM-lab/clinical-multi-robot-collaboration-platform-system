import {AbsoluteFill} from "remotion";
import type {ReactNode} from "react";

const colors = {low:"#E0BD45",normal:"#FB9966",high:"#D65B57",emergency:"#954D43"};
export type ScheduleRow = {
  code:string; title:string; route:string; robot:string; status:string;
  priority:keyof typeof colors; start:string; revised?:string;
};
export const v6Rows: readonly ScheduleRow[] = [
  {code:"T0173",title:"Waste transport",route:"Ward A → Waste return",robot:"W01",status:"Running",priority:"emergency",start:"10:55"},
  {code:"T0002",title:"Medication delivery",route:"Pharmacy → Ward A",robot:"Unassigned",status:"Pending",priority:"high",start:"14:20",revised:"15:05"},
  {code:"T0171",title:"Specimen delivery",route:"Blood draw → Laboratory",robot:"C02",status:"Pending",priority:"low",start:"14:45"},
  {code:"T0174",title:"Clothes collection",route:"Ward A → Clothes return",robot:"M02",status:"Assigned · Not started",priority:"low",start:"16:10"},
  {code:"T0172",title:"Medication delivery",route:"Pharmacy → Ward A",robot:"C01",status:"Assigned · Not started",priority:"normal",start:"16:45"},
  {code:"T0175",title:"Specimen delivery",route:"Blood draw → Laboratory",robot:"C02",status:"Assigned · Not started",priority:"normal",start:"17:00"},
];
export const wideStage={background:"#faf7f2",color:"#231d19",fontFamily:"Arial, 'Noto Sans CJK TC', sans-serif"};

export const timeOrder=(saved:boolean)=>[...v6Rows].sort((a,b)=>
  (saved?a.revised??a.start:a.start).localeCompare(saved?b.revised??b.start:b.start)).slice(0,4);

export const ScheduleTitle=({x=300,y=105,size=41,mask=0}:{x?:number;y?:number;size?:number;mask?:number})=>
  <div style={{position:"absolute",left:x,top:y,fontSize:size,fontWeight:750,letterSpacing:"-.045em",
    lineHeight:1.07,whiteSpace:"nowrap",clipPath:`inset(0 ${mask}% 0 0)`}}>
    Flexible <span style={{color:"#d65c1c"}}>scheduling.</span>
  </div>;

export const ScheduleMeta=({editing=false,opacity=1}:{editing?:boolean;opacity?:number})=>
  <div style={{position:"absolute",left:300,top:166,width:1320,height:56,display:"flex",alignItems:"center",
    justifyContent:"space-between",borderBottom:"1px solid #e7ded6",opacity}}>
    <div style={{display:"flex",alignItems:"baseline",gap:19}}>
      <strong style={{fontSize:24}}>Daily tasks</strong><span style={{fontSize:18,color:"#65574d"}}>November 21, 2026 · {v6Rows.length} tasks</span>
    </div>
    <div style={{display:"grid",placeItems:"center",width:42,height:34,border:"1px solid #ddbcaa",
      borderRadius:8,background:editing?"#ffecdf":"#fff",color:editing?"#a84c22":"#70584b"}}>
      <svg viewBox="0 0 24 24" width={18} height={18} fill="none" stroke="currentColor" strokeWidth={1.7}
        strokeLinecap="round" strokeLinejoin="round" aria-label={editing?"Done editing":"Edit"}>
        {editing?<path d="m5 12 4 4L19 6"/>:<path d="m13 6 5 5M4 20l4-.9L20 7a2.1 2.1 0 0 0-3-3L5 16z"/>}
      </svg>
    </div>
  </div>;

export const ScheduleCard=({row, y, x=300, width=1320, height=118, selected=false, time, opacity=1, edit, draft, after}:{
  row:ScheduleRow;y:number;x?:number;width?:number;height?:number;selected?:boolean;
  time:string;opacity?:number;edit?:boolean;draft?:string;after?:ReactNode;
})=>{
  const color=colors[row.priority];
  return <div style={{position:"absolute",left:x,top:y,width,height,opacity,
    display:"grid",gridTemplateColumns:"155px minmax(0, 1fr)",gap:16, alignItems:"stretch"}}>
    <div style={{padding:"18px 0 0 4px",fontSize:34,fontWeight:720,letterSpacing:"-.035em",
      fontVariantNumeric:"tabular-nums",color:selected?"#9b4e29":"#3b302a"}}>{time}</div>
    <article style={{position:"relative",boxSizing:"border-box",minWidth:0,overflow:"hidden",padding:"13px 24px 12px 24px",
      border:`1px solid color-mix(in srgb, ${color} ${selected?60:27}%, #f5e9e0)`,borderLeft:`5px solid ${color}`,borderRadius:12,
      background:`color-mix(in srgb, white ${selected?87:92}%, ${color})`,
      boxShadow:selected?"0 10px 32px #683d2418":"0 3px 11px #57372209"}}>
      <div style={{fontSize:16,color:"#665448",fontWeight:650}}>{row.code} · {row.robot}</div>
      <div style={{marginTop:4,fontSize:selected?32:27,fontWeight:730,letterSpacing:"-.025em"}}>{row.title}</div>
      <div style={{marginTop:5,fontSize:18,color:"#665448"}}>{row.route}</div>
      <div style={{position:"absolute",top:18,right:22,display:"flex",alignItems:"center",gap:11}}>
        <span style={{background:"#ffffffa6",padding:"5px 11px",borderRadius:5,fontSize:15,color:"#5e4d43",fontWeight:600}}>{row.status}</span>
        <span style={{background:`color-mix(in srgb, ${color} 15%, white)`,padding:"5px 10px",borderRadius:5,
          fontWeight:650,fontSize:15,color:"#634638",textTransform:"capitalize"}}>{row.priority}</span>
      </div>
      {edit&&<div style={{position:"absolute",top:111,left:24,right:22,borderTop:"1px solid #e9cdca",paddingTop:16,
        display:"flex",alignItems:"end",gap:25}}>
        <div><div style={{fontSize:16,color:"#665448",marginBottom:6}}>Start time</div>
          <div style={{width:195,height:48,boxSizing:"border-box",background:"white",border:"2px solid #ef965f",borderRadius:8,
            padding:"8px 11px",display:"flex",justifyContent:"space-between",alignItems:"center",fontSize:24,
            fontVariantNumeric:"tabular-nums",fontWeight:700}}>
            {draft??row.start}
            <svg viewBox="0 0 24 24" width={18} height={18} fill="none" stroke="#946e59" strokeWidth={1.6}>
              <circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 2"/>
            </svg>
          </div>
        </div>
        <div style={{height:45,padding:"0 15px",boxSizing:"border-box",display:"grid",placeItems:"center",
          background:draft===row.revised?"#ecf8f1":"#f5f4f2",color:draft===row.revised?"#367053":"#8e8179",borderRadius:8,
          border:`1px solid ${draft===row.revised?"#bbdfca":"#e4dad2"}`,fontWeight:700,fontSize:17}}>✓ Re-add task</div>
      </div>}
      {after}
    </article>
  </div>;
};

export type ScheduleKeyframe = "A" | "B" | "C";
export const ScheduleStoryboard=({phase}:{phase:ScheduleKeyframe})=>{
  const editing=phase==="B", saved=phase==="C";
  return <AbsoluteFill style={wideStage}>
    <ScheduleTitle/><ScheduleMeta editing={editing}/>
    {timeOrder(saved).map((row,i)=>{
      const hero=row.code==="T0002";
      return <ScheduleCard key={row.code} row={row} time={saved?row.revised??row.start:row.start}
        x={hero&&editing?267:300} width={hero&&editing?1386:1320} height={hero&&editing?229:118}
        y={242+i*141+(i>1&&editing?111:0)} selected={hero&&phase!=="A"} edit={hero&&editing}
        draft={editing?row.revised:undefined}/>;
    })}
    {saved&&<div style={{position:"absolute",left:466,top:835,color:"#265d40",background:"#eaf7ee",
      border:"1px solid #b5d9c1",borderRadius:8,padding:"10px 16px",fontSize:19,fontWeight:650}}>Task changes saved</div>}
  </AbsoluteFill>;
};
