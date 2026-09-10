#!/usr/bin/env python3

from dataclasses import (
    dataclass,
    field,
)

from typing import (
    Optional,
)


# ==========================================================
# Shared Constants
# ==========================================================

VALID_TASK_PRIORITIES = {
    0,  # Low
    1,  # Normal
    2,  # High
    3,  # Emergency
}


VALID_TASK_STATUSES = {
    "pending",
    "assigned",
    "running",
    "completed",
    "failed",
    "cancelled",
    "reassigning",
}


VALID_ROBOT_STATUSES = {
    "idle",
    "busy",
    "charging",
    "error",
    "offline",
}


# ==========================================================
# Task
#
# Scheduler v2 使用的標準 Task Model。
#
# 對應 Backend：
#
# RobotTask.Id
# RobotTask.TaskType
# RobotTask.Source
# RobotTask.Destination
# RobotTask.Priority
# RobotTask.RequiredCapabilities
# RobotTask.Status
# RobotTask.AssignedRobot
# RobotTask.CreatedAt
#
# created_at：
# 在 Scheduler / Simulator 中統一使用「秒」表示。
#
# 真正接 Backend 時，
# Adapter 再負責將 DateTime 轉成 timestamp / simulation time。
# ==========================================================

@dataclass
class Task:

    task_id: str

    task_type: str

    source: str

    destination: str

    priority: int

    required_capabilities: set[str] = field(
        default_factory=set
    )

    status: str = "pending"

    assigned_robot: Optional[str] = None

    created_at: float = 0.0


    def __post_init__(
        self,
    ):

        # --------------------------------------------------
        # Priority
        # --------------------------------------------------

        if (
            self.priority
            not in VALID_TASK_PRIORITIES
        ):

            raise ValueError(
                "Task priority must be one of "
                "{0, 1, 2, 3}, "
                f"got {self.priority}"
            )

        # --------------------------------------------------
        # Status
        # --------------------------------------------------

        self.status = (
            self.status
            .strip()
            .lower()
        )

        if (
            self.status
            not in VALID_TASK_STATUSES
        ):

            raise ValueError(
                "Invalid task status: "
                f"{self.status}"
            )

        # --------------------------------------------------
        # Capability
        #
        # 即使外部傳 list，
        # Scheduler 內部也統一成 set。
        # --------------------------------------------------

        self.required_capabilities = set(
            self.required_capabilities
        )

        # --------------------------------------------------
        # Time
        # --------------------------------------------------

        self.created_at = float(
            self.created_at
        )


# ==========================================================
# Robot State
#
# Scheduler v2 使用的標準 Robot State。
#
# 注意：
#
# available != idle
#
# busy Robot 只要：
#
# - 正常運作
# - Battery 足夠
# - Capability 符合
#
# 仍可以接受未來 Task，
# Task 之後會進入 Waiting Queue。
#
# 是否真正能成為 Candidate，
# 不在 Model 中判斷，
# 後續交給 candidate_filter.py。
# ==========================================================

@dataclass
class RobotState:

    robot_id: str

    fleet_name: str

    status: str

    # Scheduler 內部統一：
    #
    # 0.0 ~ 1.0
    #
    # Backend 若為 0 ~ 100，
    # Adapter 再負責轉換。
    battery: float

    x: float

    y: float

    map_name: str

    capabilities: set[str] = field(
        default_factory=set
    )

    current_task: Optional[str] = None

    available: bool = True


    def __post_init__(
        self,
    ):

        # --------------------------------------------------
        # Robot Status
        # --------------------------------------------------

        self.status = (
            self.status
            .strip()
            .lower()
        )

        if (
            self.status
            not in VALID_ROBOT_STATUSES
        ):

            raise ValueError(
                "Invalid robot status: "
                f"{self.status}"
            )

        # --------------------------------------------------
        # Battery
        # --------------------------------------------------

        self.battery = float(
            self.battery
        )

        if not (
            0.0
            <=
            self.battery
            <=
            1.0
        ):

            raise ValueError(
                "Robot battery must be "
                "between 0.0 and 1.0, "
                f"got {self.battery}"
            )

        # --------------------------------------------------
        # Position
        # --------------------------------------------------

        self.x = float(
            self.x
        )

        self.y = float(
            self.y
        )

        # --------------------------------------------------
        # Capability
        # --------------------------------------------------

        self.capabilities = set(
            self.capabilities
        )

        # --------------------------------------------------
        # available
        #
        # 不根據 status 自動修改。
        #
        # 例如：
        #
        # status = busy
        # available = True
        #
        # 是合法狀態。
        # --------------------------------------------------

        self.available = bool(
            self.available
        )