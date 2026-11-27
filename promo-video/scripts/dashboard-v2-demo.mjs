export const capturedAt = new Date("2026-11-20T10:24:00+08:00");
const batteries = [86, 64, 92, 79, 73, 52, 38];
const robotId = index => `robot-hospital_robot_${index + 1}`;

export function robotSnapshot(poll) {
  return {robots: batteries.map((battery, index) => ({
    id: robotId(index), levelName: "L1", hasTelemetry: true,
    status: index < 4 ? "執行任務中" : index === 6 ? "充電中" : "待命",
    battery: battery + (poll % 2), location: "reception_back",
    lastUpdate: capturedAt.toISOString(),
  }))};
}

const statuses = [
  ...Array(18).fill("completed"), ...Array(4).fill("running"), ...Array(2).fill("pending"),
];
const localMidnight = new Date("2026-11-20T00:00:00+08:00").getTime();
export const taskRecords = statuses.map((status, index) => {
  const minute = index < 18 ? 360 + index * 14 : 614 + (index - 18) * 3;
  const scheduledAt = new Date(localMidnight + minute * 60000).toISOString();
  return {
    id: `dashboard-fixture-${index}`, taskCode: `T${String(index + 101).padStart(4, "0")}`,
    taskType: "medication_delivery", source: "reception_back", destination: "ward_a_1",
    createdAt: scheduledAt, scheduledAt, status,
    dispatched: status !== "pending",
    assignedRobot: status === "pending" ? null : robotId(index < 18 ? index % 4 : index - 18),
  };
});
