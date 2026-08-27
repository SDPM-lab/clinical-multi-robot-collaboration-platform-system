import math

from ..base_scheduler import BaseScheduler
from scheduler.models import Task, RobotState, Assignment


class RuleBasedScheduler(BaseScheduler):
    """
    第一版 Rule-based Scheduler。

    規則：
    1. 只處理 available robot
    2. 計算 robot 到 task source 的直線距離
    3. battery < 20% 時加入 penalty
    4. 選擇 score 最低的 robot
    """

    LOW_BATTERY_THRESHOLD = 0.2

    LOW_BATTERY_PENALTY = 500.0

    def __init__(
        self,
        waypoints: dict[
            str,
            tuple[float, float]
        ],
    ):
        self.waypoints = waypoints

    def schedule(
        self,
        task: Task,
        robots: list[RobotState],
    ) -> Assignment:

        # ------------------------------------------
        # 檢查 source waypoint
        # ------------------------------------------

        if task.source not in self.waypoints:
            raise RuntimeError(
                f"Unknown source waypoint: "
                f"{task.source}"
            )

        source_x, source_y = \
            self.waypoints[task.source]

        best_robot = None

        best_score = float("inf")

        # ------------------------------------------
        # 計算每台 Robot 的分數
        # ------------------------------------------

        for robot in robots:

            # Busy / unavailable robot 不參與派工
            if not robot.available:
                continue

            dx = robot.x - source_x
            dy = robot.y - source_y

            distance = math.sqrt(
                dx * dx + dy * dy
            )

            battery_penalty = 0.0

            if (
                robot.battery
                < self.LOW_BATTERY_THRESHOLD
            ):
                battery_penalty = \
                    self.LOW_BATTERY_PENALTY

            score = (
                distance
                + battery_penalty
            )

            if score < best_score:
                best_score = score
                best_robot = robot

        # ------------------------------------------
        # 沒有可用 Robot
        # ------------------------------------------

        if best_robot is None:
            return Assignment(
                task_id=task.task_id,
                robot_id=None,
                scheduler="rule_based",
                decision_status="no_candidate",
                score=None,
            )

        # ------------------------------------------
        # 成功派工
        # ------------------------------------------

        return Assignment(
            task_id=task.task_id,
            robot_id=best_robot.robot_id,
            scheduler="rule_based",
            decision_status="assigned",
            score=best_score,
        )