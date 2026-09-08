import math

from ..base_scheduler import BaseScheduler
from scheduler.models import (
    Task,
    RobotState,
    Assignment,
)


class NearestScheduler(
    BaseScheduler
):

    """
    Nearest Robot Scheduler

    規則：
    1. robots 已經由外部完成 Capability Matching
    2. 不因 Robot Busy 而排除
    3. 只根據 Robot Queue 尾端位置到 Task Source 的距離
    4. 選擇距離最近的 Robot

    注意：
    Busy Robot 可以被預約下一筆任務。
    真正的 start_time 由 Simulator 決定：

        max(
            current_time,
            robot.available_time,
        )
    """

    def __init__(
        self,
        waypoints: dict[
            str,
            tuple[
                float,
                float,
            ]
        ],
    ):

        self.waypoints = (
            waypoints
        )


    def schedule(
        self,
        task: Task,
        robots: list[
            RobotState
        ],
    ) -> Assignment:

        # ------------------------------------------
        # Source Waypoint
        # ------------------------------------------

        if (
            task.source
            not in self.waypoints
        ):

            raise RuntimeError(
                "Unknown source waypoint: "
                f"{task.source}"
            )

        source_x, source_y = (
            self.waypoints[
                task.source
            ]
        )

        best_robot = None

        best_distance = (
            float(
                "inf"
            )
        )

        # ------------------------------------------
        # Robot Selection
        #
        # 不再檢查 robot.available。
        #
        # Busy Robot 仍可被預約。
        # ------------------------------------------

        for robot in robots:

            dx = (
                robot.x
                -
                source_x
            )

            dy = (
                robot.y
                -
                source_y
            )

            distance = (
                math.sqrt(
                    dx * dx
                    +
                    dy * dy
                )
            )

            if (
                distance
                <
                best_distance
            ):

                best_distance = (
                    distance
                )

                best_robot = (
                    robot
                )

        # ------------------------------------------
        # No Candidate
        # ------------------------------------------

        if best_robot is None:

            return Assignment(

                task_id=(
                    task.task_id
                ),

                robot_id=None,

                scheduler=(
                    "nearest"
                ),

                decision_status=(
                    "no_candidate"
                ),

                score=None,
            )

        # ------------------------------------------
        # Assigned
        # ------------------------------------------

        return Assignment(

            task_id=(
                task.task_id
            ),

            robot_id=(
                best_robot.robot_id
            ),

            scheduler=(
                "nearest"
            ),

            decision_status=(
                "assigned"
            ),

            score=(
                best_distance
            ),
        )