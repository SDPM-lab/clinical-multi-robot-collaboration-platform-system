#!/usr/bin/env python3

import math

from collections.abc import (
    Iterable,
)

from scheduler_v2.config import (
    MIN_BATTERY_LEVEL,
)

from scheduler_v2.models import (
    Task,
    RobotState,
)


# ==========================================================
# Operational Status
# ==========================================================

def is_robot_operational(
    robot: RobotState,
) -> bool:
    """
    判斷 Robot 是否處於可接受新任務的運作狀態。

    idle:
        可以接受 Task。

    busy:
        可以接受未來 Task，
        Task 之後會進入 Waiting Queue。

    charging / error / offline:
        第一版不允許接受新的 Task。
    """

    return (
        robot.status
        in {
            "idle",
            "busy",
        }
    )


# ==========================================================
# Capability Matching
# ==========================================================

def has_required_capabilities(
    task: Task,
    robot: RobotState,
) -> bool:
    """
    Robot 必須具備 Task 所有 Required Capabilities。

    例如：

    Task:
        navigation
        medicine_delivery

    Robot:
        navigation
        medicine_delivery
        manipulation

    → Match
    """

    return (
        task.required_capabilities
        .issubset(
            robot.capabilities
        )
    )


# ==========================================================
# Battery Safety
# ==========================================================

def has_safe_battery(
    robot: RobotState,
    battery_threshold: float = (
        MIN_BATTERY_LEVEL
    ),
) -> bool:
    """
    Robot battery 必須大於等於安全門檻。
    """

    battery_threshold = float(
        battery_threshold
    )

    if not (
        0.0
        <= battery_threshold
        <= 1.0
    ):

        raise ValueError(
            "battery_threshold must be "
            "between 0.0 and 1.0"
        )

    return (
        robot.battery
        >
        battery_threshold
        or
        math.isclose(
            robot.battery,
            battery_threshold,
            rel_tol=1e-9,
            abs_tol=1e-12,
        )
    )


# ==========================================================
# Feasibility
# ==========================================================

def is_feasible_robot(
    task: Task,
    robot: RobotState,
    battery_threshold: float = (
        MIN_BATTERY_LEVEL
    ),
) -> bool:
    """
    判斷 Robot 是否能成為此 Task 的候選 Robot。

    所有 Baseline 與 RL 共用：

    1. available
    2. operational status
    3. battery safety
    4. capability matching
    """

    if not robot.available:

        return False

    if not is_robot_operational(
        robot
    ):

        return False

    if not has_safe_battery(
        robot=robot,
        battery_threshold=(
            battery_threshold
        ),
    ):

        return False

    if not has_required_capabilities(
        task=task,
        robot=robot,
    ):

        return False

    return True


# ==========================================================
# Filter Candidate Robots
# ==========================================================

def filter_feasible_robots(
    task: Task,
    robots: Iterable[RobotState],
    battery_threshold: float = (
        MIN_BATTERY_LEVEL
    ),
) -> list[RobotState]:
    """
    從所有 Robot 中，
    篩選出可執行指定 Task 的 Candidate Robots。

    保留輸入順序，
    不負責決定哪一台最好。

    Robot Selection 會由：

    - Random Feasible
    - Nearest Robot
    - Weighted Heuristic
    - RL

    分別處理。
    """

    return [
        robot
        for robot in robots
        if is_feasible_robot(
            task=task,
            robot=robot,
            battery_threshold=(
                battery_threshold
            ),
        )
    ]