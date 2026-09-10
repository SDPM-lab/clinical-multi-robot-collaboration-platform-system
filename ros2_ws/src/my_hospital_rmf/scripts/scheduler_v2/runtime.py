#!/usr/bin/env python3

from dataclasses import (
    dataclass,
    field,
)

from typing import (
    Optional,
)

from scheduler_v2.config import (
    DEFAULT_ROBOT_SPEED_MPS,
)

from scheduler_v2.models import (
    Task,
    RobotState,
)


# ==========================================================
# Place
# ==========================================================

@dataclass(frozen=True)
class Place:
    """
    Scheduler / Simulator 使用的地點座標。

    Task 本身仍只保存：
        source = "pharmacy"
        destination = "ward_a"

    真正座標由 Place mapping 提供。
    """

    place_id: str

    x: float

    y: float

    map_name: str


    def __post_init__(
        self,
    ):

        object.__setattr__(
            self,
            "x",
            float(self.x),
        )

        object.__setattr__(
            self,
            "y",
            float(self.y),
        )


# ==========================================================
# Robot Runtime State
# ==========================================================

@dataclass
class RobotRuntimeState:
    """
    Scheduler / Simulator 額外維護的 Robot 排程狀態。

    RobotState：
        描述 Robot 本身目前的標準狀態。

    RobotRuntimeState：
        描述目前排程上的 Running / Waiting 狀況。
    """

    robot: RobotState

    running_task: Optional[Task] = None

    # Running Task 還剩多少秒完成。
    running_remaining_time: float = 0.0

    waiting_tasks: list[Task] = field(
        default_factory=list
    )

    robot_speed_mps: float = (
        DEFAULT_ROBOT_SPEED_MPS
    )


    def __post_init__(
        self,
    ):

        self.running_remaining_time = float(
            self.running_remaining_time
        )

        self.robot_speed_mps = float(
            self.robot_speed_mps
        )

        self.waiting_tasks = list(
            self.waiting_tasks
        )

        if self.running_remaining_time < 0.0:

            raise ValueError(
                "running_remaining_time "
                "cannot be negative"
            )

        if self.robot_speed_mps <= 0.0:

            raise ValueError(
                "robot_speed_mps "
                "must be greater than 0"
            )

        if (
            self.running_task is None
            and
            self.running_remaining_time > 0.0
        ):

            raise ValueError(
                "running_remaining_time must be 0 "
                "when running_task is None"
            )


# ==========================================================
# Task Projection
# ==========================================================

@dataclass(frozen=True)
class TaskProjection:
    """
    假設某 Task 被分配給某 Robot 後，
    該 Task 真正輪到執行時的預估狀態。
    """

    robot_id: str

    projected_x: float

    projected_y: float

    projected_map_name: str

    # ------------------------------------------------------
    # Queue / Workload
    # ------------------------------------------------------

    # Task 真正開始前預計還要等待多少工作時間。
    #
    # 不包含 Task 自己前往 Source 的時間。
    workload_before_task: float

    # 從 projected position
    # 到目前 Task source 的距離。
    distance_to_source: float

    # 在此 Task 前面的 Waiting Task 數量。
    queue_length_before_task: int

    # Debug / Dynamic Reassignment 使用。
    task_ids_before: tuple[str, ...]

    # ------------------------------------------------------
    # Battery Projection
    # ------------------------------------------------------

    # 前面的 Running / Waiting 工作考量後，
    # 輪到此 Task 開始前預計可使用的 Battery。
    projected_battery_before_task: float

    # 此 Task 自己預計需要消耗多少 Battery。
    expected_task_battery_consumption: float

    # 執行此 Task 後，
    # 預計剩餘的 Battery。
    projected_battery_after_task: float