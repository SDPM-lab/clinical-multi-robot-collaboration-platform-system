#!/usr/bin/env python3

from dataclasses import (
    dataclass,
    field,
)

from enum import (
    Enum,
)

from typing import (
    Optional,
)

from scheduler_v2.models import (
    Task,
    RobotState,
)

from scheduler_v2.runtime import (
    Place,
)


# ==========================================================
# Baseline Method
# ==========================================================

class BaselineMethod(
    str,
    Enum,
):
    """
    experiment_v2 目前支援的 Static Baselines。

    Dynamic Weighted 與 RL
    之後再加入。
    """

    RANDOM_FEASIBLE = (
        "random_feasible"
    )

    PROJECTED_NEAREST = (
        "projected_nearest"
    )

    WEIGHTED_HEURISTIC = (
        "weighted_heuristic"
    )

    DYNAMIC_WEIGHTED_HEURISTIC = (
        "dynamic_weighted_heuristic"
    )


# ==========================================================
# Simulation Scenario
# ==========================================================

@dataclass
class SimulationScenario:
    """
    一個完整 Episode 的輸入資料。

    tasks:
        Episode 中會到達的所有 Task。

    robots:
        Episode 開始時的 Robot 狀態。

    places:
        Task source / destination
        對應的地點座標。

    robot_speed_mps:
        Algorithm-level simulator
        使用的統一 Robot 移動速度。

    service_time_seconds:
        Robot 到達 Task destination 後，
        額外占用的服務時間。
    """

    name: str

    tasks: list[Task]

    robots: list[RobotState]

    places: dict[str, Place]

    robot_speed_mps: float = 1.0

    service_time_seconds: float = 30.0


    def __post_init__(
        self,
    ):

        self.tasks = list(
            self.tasks
        )

        self.robots = list(
            self.robots
        )

        self.places = dict(
            self.places
        )

        self.robot_speed_mps = float(
            self.robot_speed_mps
        )

        self.service_time_seconds = float(
            self.service_time_seconds
        )

        # --------------------------------------------------
        # Basic Parameters
        # --------------------------------------------------

        if self.robot_speed_mps <= 0.0:

            raise ValueError(
                "robot_speed_mps "
                "must be greater than 0"
            )

        if self.service_time_seconds < 0.0:

            raise ValueError(
                "service_time_seconds "
                "cannot be negative"
            )

        if not self.robots:

            raise ValueError(
                "SimulationScenario "
                "must contain at least one robot"
            )

        # --------------------------------------------------
        # Unique Task IDs
        # --------------------------------------------------

        task_ids = [
            task.task_id
            for task in self.tasks
        ]

        if (
            len(task_ids)
            !=
            len(set(task_ids))
        ):

            raise ValueError(
                "Duplicate task_id "
                "in scenario"
            )

        # --------------------------------------------------
        # Unique Robot IDs
        # --------------------------------------------------

        robot_ids = [
            robot.robot_id
            for robot in self.robots
        ]

        if (
            len(robot_ids)
            !=
            len(set(robot_ids))
        ):

            raise ValueError(
                "Duplicate robot_id "
                "in scenario"
            )

        # --------------------------------------------------
        # Task Arrival Time
        # --------------------------------------------------

        for task in self.tasks:

            if task.created_at < 0.0:

                raise ValueError(
                    "Task created_at "
                    "cannot be negative"
                )

        # --------------------------------------------------
        # Place Validation
        # --------------------------------------------------

        for task in self.tasks:

            if (
                task.source
                not in self.places
            ):

                raise ValueError(
                    "Unknown task source: "
                    f"{task.source}"
                )

            if (
                task.destination
                not in self.places
            ):

                raise ValueError(
                    "Unknown task destination: "
                    f"{task.destination}"
                )


# ==========================================================
# Task Execution Record
# ==========================================================

@dataclass
class TaskExecutionRecord:
    """
    一個 Task 在 Episode 中的實際執行紀錄。

    這不是 Backend RobotTask。

    它只屬於 Experiment，
    用來計算正式評估指標。
    """

    task_id: str

    priority: int

    arrival_time: float

    assigned_robot: Optional[str] = None

    assigned_at: Optional[float] = None

    start_time: Optional[float] = None

    completion_time: Optional[float] = None

    status: str = "pending"

    # Robot 從開始處理此 Task 起：
    #
    # current position
    # -> source
    # -> destination
    #
    # 實際產生的總移動距離。
    travel_distance: float = 0.0

    failure_reason: Optional[str] = None


    @property
    def waiting_time(
        self,
    ) -> Optional[float]:
        """
        StartTime - ArrivalTime
        """

        if self.start_time is None:

            return None

        return (
            self.start_time
            -
            self.arrival_time
        )


    @property
    def completion_duration(
        self,
    ) -> Optional[float]:
        """
        CompletionTime - ArrivalTime
        """

        if (
            self.completion_time
            is None
        ):

            return None

        return (
            self.completion_time
            -
            self.arrival_time
        )


# ==========================================================
# Scheduler Decision Record
# ==========================================================

@dataclass
class SchedulerDecisionRecord:
    """
    記錄一次 Scheduler Decision。

    assignment：
        新 Task 第一次選 Robot。

    reassignment：
        已經 Assigned、仍在 Waiting 的 Task
        因 Dynamic Event 被重新評估。

    Running Task 不允許 reassignment。
    """

    task_id: str

    simulation_time: float

    method: str

    selected_robot: Optional[str]

    decision_duration_seconds: float

    decision_type: str = "assignment"

    # Reassignment 專用：
    #
    # 此 Task 在重新評估前原本 Assigned Robot。
    previous_robot: Optional[str] = None

    # 哪一個 Dynamic Event
    # 觸發這一連串重新評估。
    #
    # 例如：
    # arrival:T0010
    # completion:T0005
    # robot_status:R2
    root_event_id: Optional[str] = None

    # assignment = 0
    #
    # 直接由 root event 觸發：
    # cascade_depth = 1
    #
    # 因前一個 reassignment
    # 又引發下一輪重新評估：
    # cascade_depth = 2, 3, ...
    cascade_depth: int = 0

    def __post_init__(self):

        self.simulation_time = float(
            self.simulation_time
        )

        self.decision_duration_seconds = float(
            self.decision_duration_seconds
        )

        self.cascade_depth = int(
            self.cascade_depth
        )

        if (
            self.decision_duration_seconds
            <
            0.0
        ):

            raise ValueError(
                "decision_duration_seconds "
                "cannot be negative"
            )

        if self.decision_type not in {
            "assignment",
            "reassignment",
        }:

            raise ValueError(
                "decision_type must be "
                "'assignment' or "
                "'reassignment'"
            )

        if self.cascade_depth < 0:

            raise ValueError(
                "cascade_depth "
                "cannot be negative"
            )

        # --------------------------------------------------
        # Assignment
        # --------------------------------------------------

        if (
            self.decision_type
            ==
            "assignment"
        ):

            if self.cascade_depth != 0:

                raise ValueError(
                    "assignment decision "
                    "must have "
                    "cascade_depth=0"
                )

        # --------------------------------------------------
        # Reassignment
        # --------------------------------------------------

        else:

            if self.previous_robot is None:

                raise ValueError(
                    "reassignment decision "
                    "requires previous_robot"
                )

            if self.selected_robot is None:

                raise ValueError(
                    "reassignment decision "
                    "requires selected_robot"
                )

            if self.root_event_id is None:

                raise ValueError(
                    "reassignment decision "
                    "requires root_event_id"
                )

            if self.cascade_depth < 1:

                raise ValueError(
                    "reassignment decision "
                    "requires "
                    "cascade_depth >= 1"
                )

    @property
    def changed(self) -> bool:
        """
        是否真的發生 Robot Change。

        Reassignment Decision 不代表
        一定會換 Robot。

        例如：

            previous_robot = R1
            selected_robot = R1

        表示有重新評估，
        但決定維持原派工。
        """

        if (
            self.decision_type
            !=
            "reassignment"
        ):

            return False

        return (
            self.previous_robot
            !=
            self.selected_robot
        )


# ==========================================================
# Robot Episode Record
# ==========================================================

@dataclass
class RobotEpisodeRecord:
    """
    每台 Robot 在完整 Episode 中
    累積的執行資訊。
    """

    robot_id: str

    total_travel_distance: float = 0.0

    busy_time: float = 0.0

    completed_tasks: int = 0


# ==========================================================
# Simulation Result
# ==========================================================

@dataclass
class SimulationResult:
    """
    完整 Episode 結果。

    metrics.py 之後只讀這個結果，
    不直接碰 Simulator 內部狀態。
    """

    scenario_name: str

    method: str

    episode_start_time: float

    episode_end_time: float

    task_records: dict[
        str,
        TaskExecutionRecord,
    ] = field(
        default_factory=dict
    )

    decision_records: list[
        SchedulerDecisionRecord
    ] = field(
        default_factory=list
    )

    robot_records: dict[
        str,
        RobotEpisodeRecord,
    ] = field(
        default_factory=dict
    )


    @property
    def episode_duration(
        self,
    ) -> float:

        return max(
            0.0,
            self.episode_end_time
            -
            self.episode_start_time,
        )