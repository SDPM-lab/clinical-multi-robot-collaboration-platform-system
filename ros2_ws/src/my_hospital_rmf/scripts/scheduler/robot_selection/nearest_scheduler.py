import math

from ..base_scheduler import BaseScheduler
from scheduler.models import Task, RobotState, Assignment


class NearestScheduler(BaseScheduler):

    def __init__(self, waypoints: dict[str, tuple[float, float]]):
        self.waypoints = waypoints

    def schedule(
        self,
        task: Task,
        robots: list[RobotState],
    ) -> Assignment:

        if task.source not in self.waypoints:
            raise RuntimeError(
                f"Unknown source waypoint: {task.source}"
            )

        source_x, source_y = self.waypoints[task.source]

        best_robot = None
        best_distance = float("inf")

        for robot in robots:

            if not robot.available:
                continue

            dx = robot.x - source_x
            dy = robot.y - source_y

            distance = math.sqrt(dx * dx + dy * dy)

            if distance < best_distance:
                best_distance = distance
                best_robot = robot

        if best_robot is None:
            return Assignment(
                task_id=task.task_id,
                robot_id=None,
                scheduler="nearest",
                decision_status="no_candidate",
                score=None,
            )

        return Assignment(
            task_id=task.task_id,
            robot_id=best_robot.robot_id,
            scheduler="nearest",
            decision_status="assigned",
            score=best_distance,
        )