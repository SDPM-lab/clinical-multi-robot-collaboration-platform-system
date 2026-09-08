import math

from ..base_scheduler import (
    BaseScheduler,
)

from scheduler.models import (
    Task,
    RobotState,
    Assignment,
)


class RuleBasedScheduler(
    BaseScheduler
):

    """
    Rule-based Robot Scheduler

    規則：
    1. robots 已經由外部完成 Capability Matching
    2. Busy Robot 仍然可以被預約
    3. 同時考慮：
       - Robot 到 Task Source 的距離
       - Robot 剩餘 Busy Time
       - Robot Battery
    4. 選擇 Score 最低的 Robot

    Score:

        distance_cost
        +
        busy_cost
        +
        battery_cost
    """

    LOW_BATTERY_THRESHOLD = (
        0.20
    )

    LOW_BATTERY_PENALTY = (
        0.3
    )

    DISTANCE_SCALE = (
        100.0
    )

    BUSY_TIME_SCALE = (
        300.0
    )


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


    # ======================================================
    # Distance Cost
    # ======================================================

    def _distance_cost(
        self,
        distance: float,
    ) -> float:

        return (
            distance
            /
            self.DISTANCE_SCALE
        )


    # ======================================================
    # Busy Time Cost
    # ======================================================

    def _busy_cost(
        self,
        remaining_busy_time: float,
    ) -> float:

        remaining_busy_time = max(
            0.0,
            remaining_busy_time,
        )

        return (
            remaining_busy_time
            /
            (
                remaining_busy_time
                +
                self.BUSY_TIME_SCALE
            )
        )


    # ======================================================
    # Battery Cost
    # ======================================================

    def _battery_cost(
        self,
        battery: float,
    ) -> float:

        if (
            battery
            <
            self.LOW_BATTERY_THRESHOLD
        ):

            return (
                self.LOW_BATTERY_PENALTY
            )

        return 0.0


    # ======================================================
    # Schedule
    # ======================================================

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

        best_score = (
            float(
                "inf"
            )
        )

        # ------------------------------------------
        # Robot Selection
        # ------------------------------------------

        for robot in robots:

            # --------------------------------------
            # Distance
            # --------------------------------------

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

            distance_cost = (
                self._distance_cost(
                    distance
                )
            )

            # --------------------------------------
            # Remaining Busy Time
            #
            # Simulator 會在 RobotState 上設定：
            #
            # robot.remaining_busy_time
            #
            # 若正式系統暫時沒有這個欄位，
            # 預設視為 0。
            # --------------------------------------

            remaining_busy_time = (
                getattr(
                    robot,
                    "remaining_busy_time",
                    0.0,
                )
            )

            busy_cost = (
                self._busy_cost(
                    remaining_busy_time
                )
            )

            # --------------------------------------
            # Battery
            # --------------------------------------

            battery_cost = (
                self._battery_cost(
                    robot.battery
                )
            )

            # --------------------------------------
            # Final Score
            # --------------------------------------

            score = (
                distance_cost
                +
                busy_cost
                +
                battery_cost
            )

            if (
                score
                <
                best_score
            ):

                best_score = (
                    score
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
                    "rule_based"
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
                "rule_based"
            ),

            decision_status=(
                "assigned"
            ),

            score=(
                best_score
            ),
        )