import {scenario} from "./task-creation-demo.mjs";

export const scheduleContext = [
  ["T0171","specimen_delivery","blood_draw","laboratory","low","pending","C02","15:35"],
  ["T0172","medication_delivery","pharmacy","ward_a_2","normal","assigned","C01","16:45"],
  ["T0173","waste_transport","ward_a_2","waste_return","emergency","running","W01","10:55"],
  ["T0174","clothes_collection","ward_a_2","clothes_return","low","assigned","M02","16:10"],
  ["T0175","specimen_delivery","blood_draw","laboratory","normal","assigned","C02","17:00"],
].map(([taskCode,taskType,source,destination,priority,status,robotId,time])=>({
  id:`film-context-${taskCode.toLowerCase()}`, taskCode, taskType, source, destination,
  priority, status, robotId, assignedRobot:robotId, createdAt:scenario.now,
  scheduledAt:`2026-11-21T${time}:00+08:00`,
}));
