#!/usr/bin/env python3

import random

from collections.abc import (
    Iterable,
    Mapping,
)

from scheduler_v2.runtime import (
    Place,
    RobotRuntimeState,
)

from scheduler_v2.config import (
    AGING_INTERVAL_SECONDS,
    BATTERY_DRAIN_PER_METER,
    MIN_BATTERY_LEVEL,
)

from scheduler_v2.models import (
    Task,
    RobotState,
)

from scheduler_v2.candidate_filter import (
    filter_feasible_robots,
)

from scheduler_v2.projected_candidate_filter import (
    filter_projected_feasible_runtimes,
)


# ==========================================================
# Random Selection From Feasible Candidates
# ==========================================================

def select_random_robot(
    candidates: Iterable[RobotState],
    rng: random.Random,
) -> RobotState | None:
    """
    從已經通過 Candidate Filter 的 Robot 中，
    等機率隨機選擇一台。

    此函式完全不考慮：

    - Distance
    - Battery level 高低
    - Workload
    - Queue length
    - Robot position

    若沒有 Candidate：
        return None
    """

    candidate_list = list(
        candidates
    )

    if not candidate_list:

        return None

    return rng.choice(
        candidate_list
    )


# ==========================================================
# Random Feasible Baseline
# ==========================================================

def select_random_feasible_robot(
    task: Task,
    robots: Iterable[RobotState],
    rng: random.Random,
    battery_threshold: float = (
        MIN_BATTERY_LEVEL
    ),
) -> RobotState | None:
    """
    Baseline 0:
    Random Feasible

    流程：

    1. 使用共同 Candidate Filter
    2. 取得所有 Feasible Robots
    3. 從中等機率隨機選擇一台

    Candidate Filter 的共同條件：

    - available = True
    - status 為 idle 或 busy
    - battery >= safety threshold
    - capability match
    """

    candidates = (
        filter_feasible_robots(
            task=task,
            robots=robots,
            battery_threshold=(
                battery_threshold
            ),
        )
    )

    return select_random_robot(
        candidates=candidates,
        rng=rng,
    )


def select_random_projected_feasible_robot(
    task: Task,
    runtimes: Iterable[RobotRuntimeState],
    places: Mapping[str, Place],
    current_time: float,
    rng,
    battery_threshold: float = (
        MIN_BATTERY_LEVEL
    ),
    aging_interval_seconds: float = (
        AGING_INTERVAL_SECONDS
    ),
    battery_drain_per_meter: float = (
        BATTERY_DRAIN_PER_METER
    ),
) -> RobotState | None:
    """
    正式 Static Simulator 使用的 Random Baseline。

    Random 只負責：
        在所有安全合法 Candidate 中隨機選擇。

    它本身不偏好：
        Distance
        Battery
        Workload
    """

    candidates = (
        filter_projected_feasible_runtimes(
            task=task,
            runtimes=runtimes,
            places=places,
            current_time=current_time,
            battery_threshold=(
                battery_threshold
            ),
            aging_interval_seconds=(
                aging_interval_seconds
            ),
            battery_drain_per_meter=(
                battery_drain_per_meter
            ),
        )
    )

    if not candidates:

        return None

    selected_runtime = (
        rng.choice(
            candidates
        )
    )

    return (
        selected_runtime.robot
    )