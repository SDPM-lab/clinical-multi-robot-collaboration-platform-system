import { writeFileSync } from "node:fs";
import {
  TASK_TYPE_BY_LABEL,
  TASK_LOCATION_IDS,
} from "../../frontend/src/config/taskTypes.js";
import { getTaskTypeColor } from "../../frontend/src/data/taskTypeColors.js";
import { robotDisplayCodes } from "../../frontend/src/config/robotDisplayCode.js";
import { getRobotVisualTheme } from "../../frontend/src/config/robotVisualThemes.js";
import en from "../../frontend/src/i18n/locales/en.js";

const batteries = [88, 74, 83, 92, 66, 78, 49];
const floorAssignments = [1, 1, 2, 1, 3, 1, 1];
const robots = robotDisplayCodes.map((code, i) => ({
  code,
  floor: floorAssignments[i],
  connected: true,
  color: getRobotVisualTheme(code).main,
  history: ["08:00", "09:00", "10:00", "11:00"].map((time, hour) => ({
    time,
    battery: batteries[i] + (3 - hour) * (i === 6 ? -3 : 2),
  })),
}));
const types = Object.values(TASK_TYPE_BY_LABEL);
const statuses = [
  "completed",
  "running",
  "completed",
  "running",
  "pending",
  "running",
  "running",
  "pending",
  ...Array(16).fill("completed"),
];
const routeLabels = {
  pharmacy: "Pharmacy",
  ward_a_2: "Ward A",
  ward_b_2: "Ward B",
  blood_draw: "Blood Draw",
  lab: "Lab",
  waste_return_2: "Waste Return",
  clothes_return_2: "Clothes Return",
  nurse_station: "Nurse Station",
};
const tasks = statuses.map((status, i) => {
  const type = types[i % types.length];
  const route = TASK_LOCATION_IDS[type];
  const time =
    i < 8
      ? [
          "10:40",
          "10:50",
          "10:54",
          "11:00",
          "11:30",
          "11:04",
          "11:06",
          "11:45",
        ][i]
      : `0${6 + Math.floor((i - 8) / 6)}:${String(((i - 8) % 6) * 9).padStart(2, "0")}`;
  const robot = status === "pending" ? null : robots[i % robots.length].code;
  return {
    id: `T${String(151 + i).padStart(4, "0")}`,
    type,
    title: en.tasks[type],
    color: getTaskTypeColor({ taskType: type }).main,
    status,
    robot,
    time,
    source:
      routeLabels[
        type === "specimen_delivery" ? "blood_draw" : route.sources[0]
      ],
    destination: routeLabels[route.destinations[0]],
  };
});
const selected = tasks[1];
const wallTime = "11:10";
const overviewTasks = tasks
  .slice(0, 6)
  .sort((a, b) => a.time.localeCompare(b.time));
writeFileSync(
  new URL("../src/dashboard-v3-demo.json", import.meta.url),
  JSON.stringify(
    {
      robots,
      overviewTasks,
      tasks,
      selected,
      wallTime,
      network: "Online",
      completion: Math.round(
        (tasks.filter((task) => task.status === "completed").length /
          tasks.length) *
          100,
      ),
    },
    null,
    2,
  ) + "\n",
);
